import json
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Dict, Any, List, Optional
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.streak import UserStreak
from app.models.meal import Meal
from app.models.tracking import Exercise, Water
from app.models.reminder import MealReminderSetting
from app.models.base import utc_now

from app.utils.date_utils import get_date_bounds_utc, get_today_local, DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)

MILESTONES = [3, 7, 14, 30, 60, 100]


class StreakService:
    @classmethod
    async def get_or_create_streak(cls, session: AsyncSession, user_id: str) -> UserStreak:
        stmt = select(UserStreak).where(UserStreak.user_id == user_id)
        res = await session.execute(stmt)
        streak = res.scalar_one_or_none()

        if not streak:
            streak = UserStreak(
                user_id=user_id,
                current_streak=0,
                longest_streak=0,
                last_completed_date=None,
                total_active_days=0,
                milestones_achieved_json="[]",
                created_at=utc_now(),
                updated_at=utc_now()
            )
            session.add(streak)
            await session.commit()
            await session.refresh(streak)

        return streak

    @classmethod
    async def get_user_timezone(cls, session: AsyncSession, user_id: str) -> ZoneInfo:
        try:
            stmt = select(MealReminderSetting).where(MealReminderSetting.user_id == user_id)
            res = await session.execute(stmt)
            rem = res.scalar_one_or_none()
            tz_str = rem.user_timezone if (rem and rem.user_timezone) else DEFAULT_TIMEZONE
            return ZoneInfo(tz_str)
        except Exception:
            return ZoneInfo(DEFAULT_TIMEZONE)

    @classmethod
    async def has_activity_on_date(cls, session: AsyncSession, user_id: str, check_date: date, tz: ZoneInfo) -> bool:
        """
        Checks if the user has completed at least one meaningful tracking action
        (Meal, Exercise, or Water) on the specified local date.
        """
        start_utc, end_utc = get_date_bounds_utc(check_date, str(tz))

        # 1. Check Meals
        meal_stmt = select(func.count(Meal.id)).where(
            Meal.user_id == user_id,
            Meal.occurred_at >= start_utc,
            Meal.occurred_at < end_utc
        )
        meal_count = (await session.execute(meal_stmt)).scalar() or 0
        if meal_count > 0:
            return True

        # 2. Check Exercise
        ex_stmt = select(func.count(Exercise.id)).where(
            Exercise.user_id == user_id,
            Exercise.recorded_at >= start_utc,
            Exercise.recorded_at < end_utc
        )
        ex_count = (await session.execute(ex_stmt)).scalar() or 0
        if ex_count > 0:
            return True

        # 3. Check Water
        w_stmt = select(func.count(Water.id)).where(
            Water.user_id == user_id,
            Water.recorded_at >= start_utc,
            Water.recorded_at < end_utc
        )
        w_count = (await session.execute(w_stmt)).scalar() or 0
        return w_count > 0

    @classmethod
    async def calculate_streak_status(
        cls,
        session: AsyncSession,
        user_id: str,
        current_date_str: Optional[str] = None,
        user_timezone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Centralized, idempotent calculation of the user's daily streak status.
        Handles consecutive days, multiple logs on same day, missed days, and milestones.
        """
        if user_timezone:
            try:
                tz = ZoneInfo(user_timezone)
            except Exception:
                tz = await cls.get_user_timezone(session, user_id)
        else:
            tz = await cls.get_user_timezone(session, user_id)

        if current_date_str:
            try:
                today = date.fromisoformat(current_date_str.split("T")[0])
            except Exception:
                today = get_today_local(str(tz))
        else:
            today = get_today_local(str(tz))

        yesterday = today - timedelta(days=1)
        today_str = today.isoformat()
        yesterday_str = yesterday.isoformat()

        streak = await cls.get_or_create_streak(session, user_id)

        # Check if user has active logs for today
        completed_today = await cls.has_activity_on_date(session, user_id, today, tz)

        # Parse achieved milestones
        try:
            achieved_milestones = json.loads(streak.milestones_achieved_json or "[]")
        except Exception:
            achieved_milestones = []

        new_milestone = None

        # Deterministically compute consecutive active days from actual activity in DB
        consecutive_days = 0
        check_d = today if completed_today else yesterday
        while True:
            had_act = await cls.has_activity_on_date(session, user_id, check_d, tz)
            if had_act:
                consecutive_days += 1
                check_d -= timedelta(days=1)
                if consecutive_days > 365:
                    break
            else:
                break

        if completed_today:
            streak.current_streak = consecutive_days
            streak.last_completed_date = today_str
            streak.longest_streak = max(streak.longest_streak, streak.current_streak)
            streak.total_active_days = max(streak.total_active_days, streak.longest_streak, consecutive_days)
            streak.updated_at = utc_now()

            # Check milestone triggers
            if streak.current_streak in MILESTONES and streak.current_streak not in achieved_milestones:
                new_milestone = streak.current_streak

            await session.commit()
            await session.refresh(streak)
        else:
            if consecutive_days > 0:
                streak.current_streak = consecutive_days
                streak.last_completed_date = yesterday_str
            else:
                streak.current_streak = 0
            
            streak.longest_streak = max(streak.longest_streak, streak.current_streak)
            streak.updated_at = utc_now()
            await session.commit()
            await session.refresh(streak)

        # Generate weekly history (7 days of current week, Monday to Sunday)
        # Find Monday of current week
        monday = today - timedelta(days=today.weekday())
        weekly_history = []
        day_initials = ["M", "T", "W", "T", "F", "S", "S"]
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for i in range(7):
            d = monday + timedelta(days=i)
            d_str = d.isoformat()
            is_d_today = (d == today)
            is_future = (d > today)

            if is_future:
                d_completed = False
            elif is_d_today:
                d_completed = completed_today
            else:
                d_completed = await cls.has_activity_on_date(session, user_id, d, tz)

            weekly_history.append({
                "date": d_str,
                "day_name": day_names[i],
                "day_initial": day_initials[i],
                "completed": d_completed,
                "logged": d_completed,
                "is_today": is_d_today,
                "is_future": is_future
            })

        return {
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
            "total_active_days": streak.total_active_days,
            "last_completed_date": streak.last_completed_date,
            "completed_today": completed_today,
            "weekly_history": weekly_history,
            "new_milestone": new_milestone,
            "milestones_achieved": achieved_milestones
        }

    @classmethod
    async def record_activity(
        cls,
        session: AsyncSession,
        user_id: str,
        action_date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Helper method to call whenever a user logs a meal, exercise, or water.
        """
        return await cls.calculate_streak_status(session, user_id, current_date_str=action_date_str)

    @classmethod
    async def acknowledge_milestone(cls, session: AsyncSession, user_id: str, milestone: int) -> bool:
        """
        Marks a milestone as celebrated so it isn't shown repeatedly.
        """
        streak = await cls.get_or_create_streak(session, user_id)
        try:
            achieved = json.loads(streak.milestones_achieved_json or "[]")
        except Exception:
            achieved = []

        if milestone not in achieved:
            achieved.append(milestone)
            streak.milestones_achieved_json = json.dumps(achieved)
            streak.updated_at = utc_now()
            await session.commit()
            return True
        return False
