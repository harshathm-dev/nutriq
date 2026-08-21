import pytest
import datetime
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.models.meal import Meal, MealItem
from app.models.tracking import Water
from app.services.streak_service import StreakService
from app.services.daily_summary_service import DailySummaryService
from app.services.food_recommendation_service import FoodRecommendationService
from app.utils.date_utils import get_date_bounds_utc

@pytest.mark.asyncio
async def test_streak_and_smart_recommendations_sync():
    async with AsyncSessionLocal() as session:
        # Create test user
        user = User(
            email=f"streak_sync_{datetime.datetime.now(datetime.timezone.utc).timestamp()}@example.com",
            password_hash="hashed_test_password"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Profile & Goal
        profile = UserProfile(
            user_id=user.id,
            name="Streak Sync Tester",
            age=28,
            gender="male",
            height_cm=175.0,
            weight_kg=80.0,
            activity_level="moderately_active",
            fitness_goal="weight_loss",
            dietary_preference="standard"
        )
        session.add(profile)

        goal = Goal(
            user_id=user.id,
            goal_type="weight_loss",
            current_weight_kg=80.0,
            target_weight_kg=72.0,
            desired_rate=0.5,
            active=True
        )
        session.add(goal)
        await session.commit()

        # Log meals on Wednesday 2026-08-19 and Thursday 2026-08-20 (Asia/Kolkata)
        # Wednesday: 2026-08-19 12:00:00 IST -> 2026-08-19 06:30:00 UTC
        wed_utc_start, _ = get_date_bounds_utc(datetime.date(2026, 8, 19), "Asia/Kolkata")
        wed_meal_time = wed_utc_start + datetime.timedelta(hours=5)

        meal_wed = Meal(
            user_id=user.id,
            meal_type="lunch",
            occurred_at=wed_meal_time
        )
        session.add(meal_wed)
        await session.flush()

        item_wed = MealItem(
            meal_id=meal_wed.id,
            food_name="Paneer Curry",
            quantity=1.0,
            serving_unit="bowl",
            grams=150.0,
            calories=400.0,
            protein_g=20.0,
            carbs_g=15.0,
            fat_g=25.0,
            fiber_g=4.0
        )
        session.add(item_wed)

        # Thursday: 2026-08-20 (Total calories = 1695 kcal, Protein = 46g, Carbs = 257g, Fat = 56g, Fiber = 22g)
        thu_utc_start, _ = get_date_bounds_utc(datetime.date(2026, 8, 20), "Asia/Kolkata")
        thu_meal_time = thu_utc_start + datetime.timedelta(hours=4)

        meal_thu_1 = Meal(
            user_id=user.id,
            meal_type="breakfast",
            occurred_at=thu_meal_time
        )
        session.add(meal_thu_1)
        await session.flush()

        item_thu_1 = MealItem(
            meal_id=meal_thu_1.id,
            food_name="Oats & Banana",
            quantity=1.0,
            serving_unit="bowl",
            grams=200.0,
            calories=895.0,
            protein_g=20.0,
            carbs_g=150.0,
            fat_g=20.0,
            fiber_g=10.0
        )
        session.add(item_thu_1)

        meal_thu_2 = Meal(
            user_id=user.id,
            meal_type="lunch",
            occurred_at=thu_meal_time + datetime.timedelta(hours=4)
        )
        session.add(meal_thu_2)
        await session.flush()

        item_thu_2 = MealItem(
            meal_id=meal_thu_2.id,
            food_name="Rice & Dal",
            quantity=1.0,
            serving_unit="plate",
            grams=250.0,
            calories=800.0,
            protein_g=26.0,
            carbs_g=107.0,
            fat_g=36.0,
            fiber_g=12.0
        )
        session.add(item_thu_2)

        # Hydration on Thursday: 2500 ml
        water_thu = Water(
            user_id=user.id,
            amount_ml=2500.0,
            recorded_at=thu_meal_time
        )
        session.add(water_thu)
        await session.commit()

        # 1. VERIFY HABIT STREAK (User logged on Wed Aug 19 and Thu Aug 20)
        streak_status = await StreakService.calculate_streak_status(session, user.id, current_date_str="2026-08-20", user_timezone="Asia/Kolkata")
        assert streak_status["current_streak"] == 2
        assert streak_status["longest_streak"] == 2
        assert streak_status["completed_today"] is True
        
        # Verify weekly_history indicator
        weekly = streak_status["weekly_history"]
        assert len(weekly) == 7

        # Wed Aug 19 must be completed
        wed_entry = next((item for item in weekly if item["date"] == "2026-08-19"), None)
        assert wed_entry is not None
        assert wed_entry["completed"] is True
        assert wed_entry["day_name"] == "Wed"

        # Thu Aug 20 must be completed
        thu_entry = next((item for item in weekly if item["date"] == "2026-08-20"), None)
        assert thu_entry is not None
        assert thu_entry["completed"] is True
        assert thu_entry["day_name"] == "Thu"

        # Sunday Aug 23 must NOT be marked completed
        sun_entry = next((item for item in weekly if item["date"] == "2026-08-23"), None)
        assert sun_entry is not None
        assert sun_entry["completed"] is False
        assert sun_entry["day_name"] == "Sun"

        # 2. VERIFY DAILY SUMMARY & SMART NUTRITION RECOMMENDATIONS DATA SYNC
        daily_summary = await DailySummaryService.get_daily_summary(
            session=session,
            user_id=user.id,
            target_date_str="2026-08-20"
        )
        
        assert daily_summary["calories"]["consumed"] == 1695.0
        cal_target = daily_summary["calories"]["target"]
        assert cal_target > 1695.0 # Positive budget remaining
        rem_cal = daily_summary["calories"]["remaining"]
        assert rem_cal == round(cal_target - 1695.0, 1)
        assert rem_cal > 0 # Must NOT be 0 kcal

        assert daily_summary["macros"]["protein"]["consumed"] == 46.0
        assert daily_summary["macros"]["protein"]["remaining"] > 0
        assert daily_summary["macros"]["carbohydrates"]["consumed"] == 257.0
        assert daily_summary["macros"]["fat"]["consumed"] == 56.0
        assert daily_summary["macros"]["fiber"]["consumed"] == 22.0
        assert daily_summary["hydration"]["consumed_ml"] == 2500.0

        # 3. VERIFY SMART FOOD RECOMMENDATIONS
        recs = await FoodRecommendationService.get_smart_recommendations(
            session=session,
            user_id=user.id,
            target_date_str="2026-08-20"
        )

        assert recs["remaining_needs"]["calories"] == rem_cal
        assert recs["remaining_needs"]["calories"] > 0 # Must NOT be 0 kcal
        assert recs["remaining_needs"]["protein_g"] > 0
        assert len(recs["recommendations"]) > 0

        # Must include warnings when appropriate
        assert "warnings" in recs
