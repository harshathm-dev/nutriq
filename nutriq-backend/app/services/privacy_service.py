import json
from typing import Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.models.meal import Meal
from app.models.tracking import Water, Exercise, WeightHistory
from app.models.ai import AIRecommendation
from app.models.privacy import ConsentRecord

class PrivacyService:
    @classmethod
    async def record_consent(cls, session: AsyncSession, user_id: str, consent_type: str, version: str = "2.0"):
        rec = ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            version=version,
            accepted_at=datetime.now(timezone.utc)
        )
        session.add(rec)
        await session.commit()
        return rec

    @classmethod
    async def get_user_consents(cls, session: AsyncSession, user_id: str):
        stmt = select(ConsentRecord).where(ConsentRecord.user_id == user_id).order_by(ConsentRecord.accepted_at.desc())
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def export_all_user_data(cls, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        # Profile
        prof_res = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        prof = prof_res.scalar_one_or_none()
        profile_data = {
            "name": prof.name, "age": prof.age, "gender": prof.gender,
            "height_cm": prof.height_cm, "weight_kg": prof.weight_kg,
            "activity_level": prof.activity_level, "fitness_goal": prof.fitness_goal
        } if prof else {}

        # Goals
        goals_res = await session.execute(select(Goal).where(Goal.user_id == user_id))
        goals = [{"goal_type": g.goal_type, "target_weight_kg": g.target_weight_kg, "active": g.active} for g in goals_res.scalars().all()]

        # Meals
        meals_res = await session.execute(select(Meal).where(Meal.user_id == user_id).options(selectinload(Meal.items)))
        meals_list = []
        for m in meals_res.scalars().all():
            meals_list.append({
                "meal_type": m.meal_type,
                "occurred_at": m.occurred_at.isoformat(),
                "items": [{"food_name": i.food_name, "quantity": i.quantity, "unit": i.serving_unit, "calories": i.calories} for i in m.items]
            })

        # Water, Exercise, Weight
        water_res = await session.execute(select(Water).where(Water.user_id == user_id))
        water_list = [{"amount_ml": w.amount_ml, "recorded_at": w.recorded_at.isoformat()} for w in water_res.scalars().all()]

        ex_res = await session.execute(select(Exercise).where(Exercise.user_id == user_id))
        ex_list = [{"type": e.type, "duration_min": e.duration_min, "burned_kcal": e.calories_burned_est, "recorded_at": e.recorded_at.isoformat()} for e in ex_res.scalars().all()]

        wt_res = await session.execute(select(WeightHistory).where(WeightHistory.user_id == user_id))
        wt_list = [{"weight_kg": wt.weight_kg, "recorded_at": wt.recorded_at.isoformat()} for wt in wt_res.scalars().all()]

        return {
            "user_id": user_id,
            "generated_at": datetime.now(timezone.utc),
            "profile": profile_data,
            "goals": goals,
            "meals": meals_list,
            "water_logs": water_list,
            "exercise_logs": ex_list,
            "weight_logs": wt_list,
            "ai_recommendations": [],
            "recipes": [],
            "custom_foods": []
        }

    @classmethod
    async def delete_user_account_cascade(cls, session: AsyncSession, user_id: str) -> bool:
        stmt = select(User).where(User.id == user_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            return False
        await session.delete(user)
        await session.commit()
        return True
