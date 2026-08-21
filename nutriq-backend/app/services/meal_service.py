from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload
from app.models.meal import Meal, MealItem, FavoriteMeal, Recipe, RecipeIngredient
from app.models.food import Food, ServingConversion
from app.models.tracking import Water, Exercise
from app.models.profile import UserProfile
from app.models.goal import Goal
from app.schemas.meal import MealCreate, MealUpdate, MealItemCreate, MealTotals
from app.services.nutrition_engine import NutritionEngine
from app.utils.date_utils import (
    get_date_bounds_utc,
    parse_datetime_with_tz,
    get_local_date,
    get_today_local,
    DEFAULT_TIMEZONE
)

class MealService:
    @classmethod
    def get_date_bounds_utc(cls, target_date: date, tz_name: str = DEFAULT_TIMEZONE) -> Tuple[datetime, datetime]:
        return get_date_bounds_utc(target_date, tz_name)

    @classmethod
    def compute_totals(cls, items: List[Any]) -> MealTotals:
        cal = sum(float(i.calories or 0) for i in items)
        pro = sum(float(i.protein_g or 0) for i in items)
        carb = sum(float(i.carbs_g or 0) for i in items)
        fat = sum(float(i.fat_g or 0) for i in items)
        fib = sum(float(i.fiber_g or 0) for i in items)
        sug = sum(float(i.sugar_g or 0) for i in items)
        sod = sum(float(i.sodium_mg or 0) for i in items)
        return MealTotals(
            calories=round(cal, 1),
            protein_g=round(pro, 1),
            carbs_g=round(carb, 1),
            fat_g=round(fat, 1),
            fiber_g=round(fib, 1),
            sugar_g=round(sug, 1),
            sodium_mg=round(sod, 1)
        )

    @classmethod
    async def create_meal(
        cls,
        session: AsyncSession,
        user_id: str,
        data: MealCreate
    ) -> Meal:
        # Determine exact occurred_at datetime in user timezone
        occurred_dt = parse_datetime_with_tz(
            date_str=data.date,
            time_str=data.time,
            fallback_dt=data.occurred_at
        )

        meal = Meal(
            user_id=user_id,
            meal_type=data.meal_type,
            occurred_at=occurred_dt,
            source=data.source or "manual",
            sync_version=1
        )
        session.add(meal)
        await session.flush()

        for item_data in data.items:
            qty = max(0.01, float(item_data.quantity if item_data.quantity is not None else (item_data.portion if item_data.portion is not None else 1.0)))
            food_name = item_data.food_name or item_data.name or ""
            serving_unit = item_data.serving_unit or "serving"
            
            grams = float(item_data.grams or 100.0)
            cal = float(item_data.calories or 0.0)
            pro = float(item_data.protein_g if item_data.protein_g is not None else (item_data.protein or 0.0))
            carb = float(item_data.carbs_g if item_data.carbs_g is not None else (item_data.carbs or 0.0))
            fat = float(item_data.fat_g if item_data.fat_g is not None else (item_data.fat or 0.0))
            fib = float(item_data.fiber_g if item_data.fiber_g is not None else (item_data.fiber or 0.0))
            sug = float(item_data.sugar_g or 0.0)
            sod = float(item_data.sodium_mg or 0.0)

            # Deterministic calculation if linked to canonical Food database
            if item_data.food_id:
                food_stmt = select(Food).where(Food.id == item_data.food_id).options(selectinload(Food.serving_conversions))
                food_res = await session.execute(food_stmt)
                food = food_res.scalar_one_or_none()
                if food:
                    if not food_name or food_name.strip().lower() in ["undefined", "null", "food"]:
                        food_name = food.name
                    unit_grams = None
                    if food.serving_conversions:
                        for sc in food.serving_conversions:
                            if sc.serving_label.strip().lower() == serving_unit.strip().lower():
                                unit_grams = sc.grams
                                break
                        if unit_grams is None:
                            for sc in food.serving_conversions:
                                if sc.serving_label.lower() in serving_unit.lower() or serving_unit.lower() in sc.serving_label.lower():
                                    unit_grams = sc.grams
                                    break
                    
                    if unit_grams is None:
                        if item_data.grams and item_data.grams > 0 and qty > 0:
                            unit_grams = item_data.grams / qty
                        else:
                            unit_grams = food.serving_size or 100.0

                    total_grams = unit_grams * qty
                    grams = round(total_grams, 1)
                    mult = total_grams / 100.0
                    cal = round(food.calories * mult, 1)
                    pro = round(food.protein_g * mult, 1)
                    carb = round(food.carbs_g * mult, 1)
                    fat = round(food.fat_g * mult, 1)
                    fib = round((food.fiber_g or 0.0) * mult, 1)
                    sug = round((food.sugar_g or 0.0) * mult, 1)
                    sod = round((food.sodium_mg or 0.0) * mult, 1)

            if not food_name or food_name.strip().lower() in ["undefined", "null"]:
                food_name = "Food Item"

            item = MealItem(
                meal_id=meal.id,
                food_id=item_data.food_id,
                food_name=food_name,
                quantity=qty,
                serving_unit=serving_unit,
                grams=grams,
                calories=cal,
                protein_g=pro,
                carbs_g=carb,
                fat_g=fat,
                fiber_g=fib,
                sugar_g=sug,
                sodium_mg=sod
            )
            session.add(item)

        await session.commit()

        # Recalculate streak
        try:
            from app.services.streak_service import StreakService
            await StreakService.record_activity(session, user_id)
        except Exception:
            pass
        
        # Reload with items
        stmt = select(Meal).where(Meal.id == meal.id).options(selectinload(Meal.items))
        res = await session.execute(stmt)
        saved = res.scalar_one()
        saved.totals = cls.compute_totals(saved.items)
        return saved

    @classmethod
    async def update_meal(
        cls,
        session: AsyncSession,
        user_id: str,
        meal_id: str,
        data: MealUpdate
    ) -> Optional[Meal]:
        stmt = select(Meal).where(and_(Meal.id == meal_id, Meal.user_id == user_id)).options(selectinload(Meal.items))
        res = await session.execute(stmt)
        meal = res.scalar_one_or_none()
        if not meal:
            return None

        if data.meal_type is not None:
            meal.meal_type = data.meal_type

        # Update date/time only if explicitly provided
        if data.date is not None or data.time is not None or data.occurred_at is not None:
            meal.occurred_at = parse_datetime_with_tz(
                date_str=data.date,
                time_str=data.time,
                fallback_dt=data.occurred_at or meal.occurred_at
            )

        meal.sync_version = (meal.sync_version or 1) + 1

        if data.items is not None:
            del_stmt = delete(MealItem).where(MealItem.meal_id == meal.id)
            await session.execute(del_stmt)
            await session.flush()
            session.expire(meal, ['items'])

            for item_data in data.items:
                qty = max(0.01, float(item_data.quantity if item_data.quantity is not None else (item_data.portion if item_data.portion is not None else 1.0)))
                food_name = item_data.food_name or item_data.name or ""
                serving_unit = item_data.serving_unit or "serving"
                grams = float(item_data.grams or 100.0)
                cal = float(item_data.calories or 0.0)
                pro = float(item_data.protein_g if item_data.protein_g is not None else (item_data.protein or 0.0))
                carb = float(item_data.carbs_g if item_data.carbs_g is not None else (item_data.carbs or 0.0))
                fat = float(item_data.fat_g if item_data.fat_g is not None else (item_data.fat or 0.0))
                fib = float(item_data.fiber_g if item_data.fiber_g is not None else (item_data.fiber or 0.0))
                sug = float(item_data.sugar_g or 0.0)
                sod = float(item_data.sodium_mg or 0.0)

                if item_data.food_id:
                    food_stmt = select(Food).where(Food.id == item_data.food_id).options(selectinload(Food.serving_conversions))
                    food_res = await session.execute(food_stmt)
                    food = food_res.scalar_one_or_none()
                    if food:
                        if not food_name or food_name.strip().lower() in ["undefined", "null", "food"]:
                            food_name = food.name
                        unit_grams = None
                        if food.serving_conversions:
                            for sc in food.serving_conversions:
                                if sc.serving_label.strip().lower() == serving_unit.strip().lower():
                                    unit_grams = sc.grams
                                    break
                            if unit_grams is None:
                                for sc in food.serving_conversions:
                                    if sc.serving_label.lower() in serving_unit.lower() or serving_unit.lower() in sc.serving_label.lower():
                                        unit_grams = sc.grams
                                        break
                        
                        if unit_grams is None:
                            if item_data.grams and item_data.grams > 0 and qty > 0:
                                unit_grams = item_data.grams / qty
                            else:
                                unit_grams = food.serving_size or 100.0

                        total_grams = unit_grams * qty
                        grams = round(total_grams, 1)
                        mult = total_grams / 100.0
                        cal = round(food.calories * mult, 1)
                        pro = round(food.protein_g * mult, 1)
                        carb = round(food.carbs_g * mult, 1)
                        fat = round(food.fat_g * mult, 1)
                        fib = round((food.fiber_g or 0.0) * mult, 1)
                        sug = round((food.sugar_g or 0.0) * mult, 1)
                        sod = round((food.sodium_mg or 0.0) * mult, 1)

                if not food_name or food_name.strip().lower() in ["undefined", "null"]:
                    food_name = "Food Item"

                item = MealItem(
                    meal_id=meal.id,
                    food_id=item_data.food_id,
                    food_name=food_name,
                    quantity=qty,
                    serving_unit=serving_unit,
                    grams=grams,
                    calories=cal,
                    protein_g=pro,
                    carbs_g=carb,
                    fat_g=fat,
                    fiber_g=fib,
                    sugar_g=sug,
                    sodium_mg=sod
                )
                session.add(item)
        await session.commit()

        # Recalculate streak
        try:
            from app.services.streak_service import StreakService
            await StreakService.calculate_streak_status(session, user_id)
        except Exception:
            pass

        # Reload with items
        stmt = select(Meal).where(Meal.id == meal_id).options(selectinload(Meal.items))
        res = await session.execute(stmt)
        saved = res.scalar_one()
        saved.totals = cls.compute_totals(saved.items)
        return saved

    @classmethod
    async def delete_meal(
        cls,
        session: AsyncSession,
        user_id: str,
        meal_id: str
    ) -> bool:
        stmt = select(Meal).where(and_(Meal.id == meal_id, Meal.user_id == user_id))
        res = await session.execute(stmt)
        meal = res.scalar_one_or_none()
        if not meal:
            return False
        await session.delete(meal)
        await session.commit()
        return True

    @classmethod
    async def get_user_meals(
        cls,
        session: AsyncSession,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Meal]:
        q = select(Meal).where(Meal.user_id == user_id).options(selectinload(Meal.items)).order_by(Meal.occurred_at.desc())
        if start_date:
            q = q.where(Meal.occurred_at >= start_date)
        if end_date:
            q = q.where(Meal.occurred_at <= end_date)
        result = await session.execute(q)
        meals = list(result.scalars().all())
        for m in meals:
            m.totals = cls.compute_totals(m.items)
        return meals

    @classmethod
    async def get_today_meals(
        cls,
        session: AsyncSession,
        user_id: str,
        tz_name: str = DEFAULT_TIMEZONE
    ) -> List[Meal]:
        """
        Retrieves ONLY meals logged on today's calendar date in the user's timezone.
        Returns meals sorted in ascending chronological order (oldest to newest).
        """
        today_local = get_today_local(tz_name)
        start_utc, end_utc = get_date_bounds_utc(today_local, tz_name)

        stmt = select(Meal).where(
            Meal.user_id == user_id,
            Meal.occurred_at >= start_utc,
            Meal.occurred_at < end_utc
        ).options(selectinload(Meal.items)).order_by(Meal.occurred_at.asc())

        res = await session.execute(stmt)
        meals = list(res.scalars().all())
        for m in meals:
            m.totals = cls.compute_totals(m.items)
        return meals

    @classmethod
    async def get_meals_by_date(
        cls,
        session: AsyncSession,
        user_id: str,
        target_date: date,
        tz_name: str = DEFAULT_TIMEZONE
    ) -> Dict[str, Any]:
        """
        Retrieves all meals for a specific calendar date along with target and aggregated nutrition metrics.
        """
        today_local = get_today_local(tz_name)
        is_today = (target_date == today_local)
        is_future = (target_date > today_local)
        display_date_str = target_date.strftime("%A, %B %d, %Y")

        start_utc, end_utc = get_date_bounds_utc(target_date, tz_name)

        # 1. Fetch User Targets
        prof_res = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = prof_res.scalar_one_or_none()

        goal_res = await session.execute(select(Goal).where(Goal.user_id == user_id, Goal.active == True))
        goal = goal_res.scalar_one_or_none()

        if profile and goal:
            targets = NutritionEngine.calculate_targets(
                weight_kg=profile.weight_kg,
                height_cm=profile.height_cm,
                age=profile.age,
                gender=profile.gender,
                activity_level=profile.activity_level,
                fitness_goal=goal.goal_type,
                desired_rate=goal.desired_rate,
                dietary_preference=profile.dietary_preference
            )
        elif profile:
            targets = NutritionEngine.calculate_targets(
                weight_kg=profile.weight_kg,
                height_cm=profile.height_cm,
                age=profile.age,
                gender=profile.gender,
                activity_level=profile.activity_level,
                fitness_goal=profile.fitness_goal,
                desired_rate=0.5,
                dietary_preference=profile.dietary_preference
            )
        else:
            targets = {
                "target_calories": 2000.0,
                "protein_g": 100.0,
                "carbs_g": 250.0,
                "fat_g": 60.0,
                "fiber_g": 28.0,
                "water_ml": 2500.0
            }

        cal_target = round(float(targets.get("target_calories", 2000.0)), 1)
        pro_target = round(float(targets.get("protein_g", 100.0)), 1)
        carb_target = round(float(targets.get("carbs_g", 250.0)), 1)
        fat_target = round(float(targets.get("fat_g", 60.0)), 1)
        fib_target = round(float(targets.get("fiber_g", 28.0)), 1)
        water_target = round(float(targets.get("water_ml", 2500.0)), 1)

        # 2. Fetch Meals
        meal_stmt = select(Meal).where(
            Meal.user_id == user_id,
            Meal.occurred_at >= start_utc,
            Meal.occurred_at < end_utc
        ).options(selectinload(Meal.items)).order_by(Meal.occurred_at.asc())

        meal_res = await session.execute(meal_stmt)
        meals = list(meal_res.scalars().all())

        # 3. Fetch Hydration
        water_stmt = select(Water).where(
            Water.user_id == user_id,
            Water.recorded_at >= start_utc,
            Water.recorded_at < end_utc
        )
        water_res = await session.execute(water_stmt)
        water_logs = list(water_res.scalars().all())
        total_water = sum(float(w.amount_ml or 0) for w in water_logs)

        # 4. Fetch Exercise
        ex_stmt = select(Exercise).where(
            Exercise.user_id == user_id,
            Exercise.recorded_at >= start_utc,
            Exercise.recorded_at < end_utc
        )
        ex_res = await session.execute(ex_stmt)
        ex_logs = list(ex_res.scalars().all())
        total_burned = sum(float(e.calories_burned_est or 0) for e in ex_logs)

        total_cal = 0.0
        total_pro = 0.0
        total_carb = 0.0
        total_fat = 0.0
        total_fib = 0.0

        for m in meals:
            m.totals = cls.compute_totals(m.items)
            for item in m.items:
                total_cal += float(item.calories or 0)
                total_pro += float(item.protein_g or 0)
                total_carb += float(item.carbs_g or 0)
                total_fat += float(item.fat_g or 0)
                total_fib += float(item.fiber_g or 0)

        has_data = len(meals) > 0 or len(water_logs) > 0 or len(ex_logs) > 0

        return {
            "date": target_date.isoformat(),
            "display_date": display_date_str,
            "is_today": is_today,
            "is_future": is_future,
            "has_data": has_data,
            "total_calories": round(total_cal, 1),
            "total_protein": round(total_pro, 1),
            "total_carbs": round(total_carb, 1),
            "total_fat": round(total_fat, 1),
            "total_fiber": round(total_fib, 1),
            "target_calories": cal_target,
            "target_protein": pro_target,
            "target_carbs": carb_target,
            "target_fat": fat_target,
            "target_fiber": fib_target,
            "water_ml": round(total_water, 1),
            "water_target_ml": water_target,
            "exercise_calories": round(total_burned, 1),
            "meal_count": len(meals),
            "meals": meals
        }

    @classmethod
    async def get_meals_history_range(
        cls,
        session: AsyncSession,
        user_id: str,
        start_date: date,
        end_date: date,
        tz_name: str = DEFAULT_TIMEZONE
    ) -> Dict[str, Any]:
        """
        Retrieves summary statistics for each calendar day in the range [start_date, end_date].
        """
        today_local = get_today_local(tz_name)
        total_days = (end_date - start_date).days + 1
        days_out = []
        grand_total_meals = 0

        for i in range(total_days):
            cur_date = start_date + timedelta(days=i)
            start_utc, end_utc = get_date_bounds_utc(cur_date, tz_name)

            meal_stmt = select(Meal).where(
                Meal.user_id == user_id,
                Meal.occurred_at >= start_utc,
                Meal.occurred_at < end_utc
            ).options(selectinload(Meal.items))

            meal_res = await session.execute(meal_stmt)
            cur_meals = list(meal_res.scalars().all())

            cal = 0.0
            pro = 0.0
            carb = 0.0
            fat = 0.0

            for m in cur_meals:
                for item in m.items:
                    cal += float(item.calories or 0)
                    pro += float(item.protein_g or 0)
                    carb += float(item.carbs_g or 0)
                    fat += float(item.fat_g or 0)

            grand_total_meals += len(cur_meals)

            days_out.append({
                "date": cur_date.isoformat(),
                "display_date": cur_date.strftime("%b %d"),
                "total_calories": round(cal, 1),
                "total_protein": round(pro, 1),
                "total_carbs": round(carb, 1),
                "total_fat": round(fat, 1),
                "meal_count": len(cur_meals),
                "is_today": (cur_date == today_local)
            })

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days_out,
            "total_meals": grand_total_meals
        }
