from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.models.user import User
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.schemas.goal import NutritionTargetsOut
from app.middleware.auth_middleware import get_current_user
from app.services.nutrition_engine import NutritionEngine

router = APIRouter(tags=["Calories & Nutrition Targets"])

@router.post("/calculate/calories", response_model=NutritionTargetsOut)
async def calculate_calories(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str = "moderately_active",
    fitness_goal: str = "maintain",
    desired_rate: float = 0.5,
    dietary_preference: str = "standard"
):
    targets = NutritionEngine.calculate_targets(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=gender,
        activity_level=activity_level,
        fitness_goal=fitness_goal,
        desired_rate=desired_rate,
        dietary_preference=dietary_preference
    )
    return NutritionTargetsOut(**targets)

@router.get("/nutrition/targets", response_model=NutritionTargetsOut)
async def get_user_nutrition_targets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    prof_res = await session.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    prof = prof_res.scalar_one_or_none()

    goal_res = await session.execute(select(Goal).where(Goal.user_id == current_user.id, Goal.active == True))
    goal = goal_res.scalar_one_or_none()

    weight_kg = prof.weight_kg if prof else 70.0
    height_cm = prof.height_cm if prof else 175.0
    age = prof.age if prof else 25
    gender = prof.gender if prof else "male"
    activity_level = prof.activity_level if prof else "moderately_active"
    dietary_preference = prof.dietary_preference if prof else "standard"
    fitness_goal = goal.goal_type if goal else "maintain"
    desired_rate = goal.desired_rate if goal else 0.5

    targets = NutritionEngine.calculate_targets(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=gender,
        activity_level=activity_level,
        fitness_goal=fitness_goal,
        desired_rate=desired_rate,
        dietary_preference=dietary_preference
    )
    return NutritionTargetsOut(**targets)
