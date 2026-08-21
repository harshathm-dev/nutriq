from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.reminder import MealReminderSetting, MealReminderLog
from app.models.meal import Meal
from app.models.profile import UserProfile
from app.utils.date_utils import get_today_local, get_date_bounds_utc


class ReminderService:
    @classmethod
    async def get_or_create_settings(cls, session: AsyncSession, user_id: str) -> MealReminderSetting:
        stmt = select(MealReminderSetting).where(MealReminderSetting.user_id == user_id)
        res = await session.execute(stmt)
        setting = res.scalar_one_or_none()

        if not setting:
            setting = MealReminderSetting(
                user_id=user_id,
                reminders_enabled=True,
                breakfast_enabled=True,
                breakfast_time="08:00",
                lunch_enabled=True,
                lunch_time="13:00",
                snack_enabled=True,
                snack_time="17:00",
                dinner_enabled=True,
                dinner_time="20:00",
                grace_period_minutes=30,
                daily_summary_enabled=True,
                daily_summary_time="20:30",
                user_timezone="Asia/Kolkata"
            )
            session.add(setting)
            await session.commit()
            await session.refresh(setting)

        return setting

    @classmethod
    async def update_settings(cls, session: AsyncSession, user_id: str, updates: Dict[str, Any]) -> MealReminderSetting:
        setting = await cls.get_or_create_settings(session, user_id)

        for k, v in updates.items():
            if v is not None and hasattr(setting, k):
                setattr(setting, k, v)

        await session.commit()
        await session.refresh(setting)
        return setting

    @classmethod
    async def get_pending_reminders(
        cls,
        session: AsyncSession,
        user_id: str,
        current_time_iso: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates reminder triggers against the user's real-time meal journal.
        Returns the highest-priority pending reminder if due and unlogged.
        """
        setting = await cls.get_or_create_settings(session, user_id)
        if not setting.reminders_enabled:
            return {"has_pending": False}

        # Determine user local time
        today_date = get_today_local()
        today_str = today_date.isoformat()

        if current_time_iso:
            try:
                clean_iso = current_time_iso.rstrip("Z")
                parsed_dt = datetime.fromisoformat(clean_iso)
                now_local = datetime(today_date.year, today_date.month, today_date.day, parsed_dt.hour, parsed_dt.minute, parsed_dt.second, tzinfo=timezone.utc)
            except Exception:
                now_local = datetime.now(timezone.utc)
        else:
            now_local = datetime.now(timezone.utc)

        current_minutes = now_local.hour * 60 + now_local.minute

        # Fetch today's logged meals
        user_tz = "Asia/Kolkata"
        start_of_day_utc, end_of_day_utc = get_date_bounds_utc(today_date, user_tz)

        meal_stmt = select(Meal).where(
            Meal.user_id == user_id,
            Meal.occurred_at >= start_of_day_utc,
            Meal.occurred_at < end_of_day_utc
        )
        meal_res = await session.execute(meal_stmt)
        meals = list(meal_res.scalars().all())

        logged_types = set()
        for m in meals:
            m_type = (m.meal_type or "snack").lower()
            if "breakfast" in m_type or "morning" in m_type:
                logged_types.add("breakfast")
            elif "lunch" in m_type or "afternoon" in m_type:
                logged_types.add("lunch")
            elif "dinner" in m_type or "night" in m_type or "supper" in m_type:
                logged_types.add("dinner")
            else:
                logged_types.add("snack")

        # Meal schedules
        meal_configs = [
            {
                "type": "breakfast",
                "enabled": setting.breakfast_enabled,
                "time": setting.breakfast_time or "08:00",
                "title": "🍳 Breakfast Reminder",
                "message": "You haven't logged your breakfast yet. Add it to NutriQ to keep your nutrition tracking up to date.",
                "action_url": "/log-meal?meal_type=breakfast"
            },
            {
                "type": "lunch",
                "enabled": setting.lunch_enabled,
                "time": setting.lunch_time or "13:00",
                "title": "🍽️ Lunch Reminder",
                "message": "You haven't logged your lunch yet. Add it to NutriQ to keep your nutrition tracking up to date.",
                "action_url": "/log-meal?meal_type=lunch"
            },
            {
                "type": "snack",
                "enabled": setting.snack_enabled,
                "time": setting.snack_time or "17:00",
                "title": "🥗 Evening Snack Reminder",
                "message": "You haven't logged your evening snack yet. Add it to NutriQ to keep your nutrition tracking up to date.",
                "action_url": "/log-meal?meal_type=snack"
            },
            {
                "type": "dinner",
                "enabled": setting.dinner_enabled,
                "time": setting.dinner_time or "20:00",
                "title": "🍲 Dinner Reminder",
                "message": "You haven't logged your dinner yet. Add it to NutriQ to keep your nutrition tracking up to date.",
                "action_url": "/log-meal?meal_type=dinner"
            }
        ]

        # Fetch existing logs for today
        log_stmt = select(MealReminderLog).where(
            MealReminderLog.user_id == user_id,
            MealReminderLog.date == today_str
        )
        log_res = await session.execute(log_stmt)
        existing_logs = {l.meal_type: l for l in log_res.scalars().all()}

        grace_period = setting.grace_period_minutes or 30

        # Check Meal Reminders
        for cfg in meal_configs:
            m_type = cfg["type"]
            if not cfg["enabled"]:
                continue

            # If user logged the meal in journal, auto-mark completed in logs
            if m_type in logged_types:
                if m_type in existing_logs and not existing_logs[m_type].completed:
                    existing_logs[m_type].completed = True
                    await session.commit()
                continue

            log_entry = existing_logs.get(m_type)
            if log_entry and (log_entry.completed or log_entry.dismissed):
                continue

            # Parse scheduled time
            try:
                h, m = map(int, cfg["time"].split(":"))
                scheduled_minutes = h * 60 + m
            except Exception:
                continue

            # Calculate trigger time with grace period & remind_later offsets
            remind_later_offset = (log_entry.remind_later_count * 30) if log_entry else 0
            trigger_minutes = scheduled_minutes + grace_period + remind_later_offset

            if current_minutes >= trigger_minutes:
                # Check if max remind later reached
                remind_count = log_entry.remind_later_count if log_entry else 0
                if remind_count >= 2 and log_entry and log_entry.reminder_sent:
                    # Max 2 reminders reached
                    continue

                # Prepare log entry if not existing
                if not log_entry:
                    log_entry = MealReminderLog(
                        user_id=user_id,
                        meal_type=m_type,
                        date=today_str,
                        reminder_sent=True,
                        last_reminded_at=datetime.now(timezone.utc)
                    )
                    session.add(log_entry)
                    await session.commit()

                return {
                    "has_pending": True,
                    "meal_type": m_type,
                    "title": cfg["title"],
                    "message": cfg["message"],
                    "scheduled_time": cfg["time"],
                    "remind_later_count": remind_count,
                    "can_remind_later": (remind_count < 2),
                    "action_url": cfg["action_url"],
                    "date": today_str
                }

        # Check Daily Summary Reminder
        if setting.daily_summary_enabled:
            summary_log = existing_logs.get("daily_summary")
            if not (summary_log and (summary_log.completed or summary_log.dismissed)):
                try:
                    sh, sm = map(int, (setting.daily_summary_time or "20:30").split(":"))
                    summary_minutes = sh * 60 + sm
                    if current_minutes >= summary_minutes:
                        if not summary_log:
                            summary_log = MealReminderLog(
                                user_id=user_id,
                                meal_type="daily_summary",
                                date=today_str,
                                reminder_sent=True,
                                last_reminded_at=datetime.now(timezone.utc)
                            )
                            session.add(summary_log)
                            await session.commit()

                        return {
                            "has_pending": True,
                            "meal_type": "daily_summary",
                            "title": "📊 NutriQ Daily Summary",
                            "message": "Your NutriQ daily summary is ready.",
                            "scheduled_time": setting.daily_summary_time or "20:30",
                            "remind_later_count": 0,
                            "can_remind_later": False,
                            "action_url": "/daily-summary",
                            "date": today_str
                        }
                except Exception:
                    pass

        return {"has_pending": False}

    @classmethod
    async def handle_reminder_action(
        cls,
        session: AsyncSession,
        user_id: str,
        meal_type: str,
        action: str,
        target_date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handles user interactions with reminders:
        - log_meal: marks reminder completed
        - remind_later: increments count (up to 2) and delays 30 mins
        - dismiss: stops further reminders for this meal today
        """
        today_str = target_date_str or datetime.now(timezone.utc).date().isoformat()

        stmt = select(MealReminderLog).where(
            MealReminderLog.user_id == user_id,
            MealReminderLog.meal_type == meal_type,
            MealReminderLog.date == today_str
        )
        res = await session.execute(stmt)
        log_entry = res.scalar_one_or_none()

        if not log_entry:
            log_entry = MealReminderLog(
                user_id=user_id,
                meal_type=meal_type,
                date=today_str
            )
            session.add(log_entry)

        if action == "log_meal":
            log_entry.completed = True
            log_entry.dismissed = False
        elif action == "remind_later":
            current_cnt = log_entry.remind_later_count if log_entry.remind_later_count is not None else 0
            log_entry.remind_later_count = min(2, current_cnt + 1)
            log_entry.reminder_sent = False  # Reset so it triggers 30m later
            log_entry.last_reminded_at = datetime.now(timezone.utc)
        elif action == "dismiss":
            log_entry.dismissed = True

        await session.commit()
        return {
            "status": "success",
            "meal_type": meal_type,
            "action": action,
            "completed": log_entry.completed,
            "dismissed": log_entry.dismissed,
            "remind_later_count": log_entry.remind_later_count
        }
