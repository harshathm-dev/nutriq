import asyncio
import os
import sys
from datetime import datetime, date

# Ensure backend path is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.models.user import User
from app.models.meal import Meal, MealItem
from app.models.food import Food
from app.schemas.meal import MealCreate, MealItemCreate, MealOut
from app.services.meal_service import MealService
from app.services.analytics_service import AnalyticsService
from app.utils.date_utils import get_today_local, DEFAULT_TIMEZONE

async def run_test():
    db_path = os.path.join(backend_dir, "nutriq.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Fetch or create a test user
        user_stmt = select(User).limit(1)
        user_res = await session.execute(user_stmt)
        test_user = user_res.scalar_one_or_none()
        if not test_user:
            print("No test user found, creating test user...")
            test_user = User(
                id="test_user_analytics_123",
                email="analytics_tester@nutriq.test",
                full_name="Analytics Tester",
                is_active=True
            )
            session.add(test_user)
            await session.commit()

        user_id = test_user.id
        today_local = get_today_local(DEFAULT_TIMEZONE)
        today_str = today_local.isoformat()

        print(f"Testing with User ID: {user_id}, Today Local: {today_str}")

        # 2. Look up foods in Food Catalog: Plain Dosa, Sambar, Coconut Chutney, Curd Rice
        dosa_stmt = select(Food).where(Food.name.ilike("%Plain Dosa%")).limit(1)
        sambar_stmt = select(Food).where(Food.name.ilike("%Sambar%")).limit(1)
        chutney_stmt = select(Food).where(Food.name.ilike("%Coconut Chutney%")).limit(1)
        curd_rice_stmt = select(Food).where(Food.name.ilike("%Curd Rice%")).limit(1)

        dosa = (await session.execute(dosa_stmt)).scalar_one_or_none()
        sambar = (await session.execute(sambar_stmt)).scalar_one_or_none()
        chutney = (await session.execute(chutney_stmt)).scalar_one_or_none()
        curd_rice = (await session.execute(curd_rice_stmt)).scalar_one_or_none()

        print(f"Catalog Check - Dosa: {dosa.name if dosa else 'N/A'}, Sambar: {sambar.name if sambar else 'N/A'}, Chutney: {chutney.name if chutney else 'N/A'}, Curd Rice: {curd_rice.name if curd_rice else 'N/A'}")

        # 3. Log Breakfast with 3 items:
        # - 2x Plain Dosa
        # - 1x Sambar
        # - 1x Coconut Chutney
        breakfast_data = MealCreate(
            meal_type="breakfast",
            date=today_str,
            time="08:30",
            source="test_runner",
            items=[
                MealItemCreate(
                    food_id=dosa.id if dosa else None,
                    food_name="Plain Dosa",
                    quantity=2.0,
                    portion=2.0,
                    serving_unit="piece",
                    grams=160.0,
                    calories=268.0,
                    protein_g=6.2,
                    carbs_g=47.0,
                    fat_g=5.9,
                    fiber_g=2.9
                ),
                MealItemCreate(
                    food_id=sambar.id if sambar else None,
                    food_name="Sambar",
                    quantity=1.0,
                    portion=1.0,
                    serving_unit="cup",
                    grams=150.0,
                    calories=110.0,
                    protein_g=4.5,
                    carbs_g=18.0,
                    fat_g=2.5,
                    fiber_g=3.8
                ),
                MealItemCreate(
                    food_id=chutney.id if chutney else None,
                    food_name="Coconut Chutney",
                    quantity=1.0,
                    portion=1.0,
                    serving_unit="tbsp",
                    grams=30.0,
                    calories=75.0,
                    protein_g=0.8,
                    carbs_g=2.1,
                    fat_g=7.2,
                    fiber_g=1.2
                )
            ]
        )

        saved_breakfast = await MealService.create_meal(session, user_id, breakfast_data)
        print(f"\n[OK] Breakfast logged: ID={saved_breakfast.id}, Total Calories={saved_breakfast.totals.calories}")
        for it in saved_breakfast.items:
            print(f"   -> Item: {it.quantity}x {it.food_name} | {it.calories} kcal | P:{it.protein_g}g C:{it.carbs_g}g F:{it.fat_g}g")

        # 4. Log Lunch: 1x Curd Rice
        lunch_data = MealCreate(
            meal_type="lunch",
            date=today_str,
            time="13:15",
            source="test_runner",
            items=[
                MealItemCreate(
                    food_id=curd_rice.id if curd_rice else None,
                    food_name="Curd Rice",
                    quantity=1.0,
                    portion=1.0,
                    serving_unit="bowl",
                    grams=200.0,
                    calories=240.0,
                    protein_g=5.6,
                    carbs_g=38.0,
                    fat_g=6.5,
                    fiber_g=1.0
                )
            ]
        )

        saved_lunch = await MealService.create_meal(session, user_id, lunch_data)
        print(f"\n[OK] Lunch logged: ID={saved_lunch.id}, Total Calories={saved_lunch.totals.calories}")
        for it in saved_lunch.items:
            print(f"   -> Item: {it.quantity}x {it.food_name} | {it.calories} kcal | P:{it.protein_g}g C:{it.carbs_g}g F:{it.fat_g}g")

        # 5. Verify Today's Meals endpoint query
        today_meals = await MealService.get_today_meals(session, user_id)
        print(f"\n[OK] Today's Meals count: {len(today_meals)}")
        assert len(today_meals) >= 2, "Expected at least 2 meals today"

        # Validate serialization into MealOut
        for m in today_meals:
            out = MealOut.model_validate(m)
            out_dict = out.model_dump()
            print(f"\nMeal: {out_dict['meal_type']} ({out_dict['meal_time']}) - {out_dict['total_calories']} kcal (Totals: {out_dict['totals']['calories']})")
            assert out_dict['total_calories'] > 0, "Meal calories must be > 0"
            assert len(out_dict['items']) > 0, "Meal must have items"
            for it in out_dict['items']:
                print(f"   - {it['quantity']}x {it['food_name']} (name alias: '{it['name']}') => {it['calories']} kcal")
                assert it['food_name'] not in [None, 'undefined', 'null', ''], f"Invalid food_name: {it['food_name']}"
                assert it['quantity'] > 0, f"Invalid quantity: {it['quantity']}"

        # 6. Verify Comprehensive Analytics Range
        print("\nTesting Analytics Service Range (7d, 30d, 90d)...")
        analytics_7d = await AnalyticsService.get_analytics_range(session, user_id, range_key="7d")
        print(f"7d Analytics: Total tracked days = {analytics_7d['summary']['total_tracked_days']}, Avg Cal = {analytics_7d['summary']['avg_calories']} kcal")
        assert analytics_7d['summary']['avg_calories'] > 0, "7d average calories should be > 0"
        assert len(analytics_7d['calories']) == 7, "7d should have 7 calorie points"
        assert len(analytics_7d['hydration']) == 7, "7d should have 7 hydration points"
        assert len(analytics_7d['macros']) == 7, "7d should have 7 macro points"
        assert len(analytics_7d['protein']) == 7, "7d should have 7 protein points"
        assert len(analytics_7d['activity']) == 7, "7d should have 7 activity points"
        assert len(analytics_7d['calorie_balance']) == 7, "7d should have 7 balance points"

        print("\nAll Backend Meal and Analytics contract integrity tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_test())
