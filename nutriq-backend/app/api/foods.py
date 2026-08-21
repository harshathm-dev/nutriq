from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from app.database.session import get_db
from app.models.user import User
from app.models.food import Food, ServingConversion, CustomFood, UserFavoriteFood
from app.models.meal import Meal, MealItem
from app.schemas.food import FoodOut, FoodCreate, CustomFoodCreate, CustomFoodOut
from app.middleware.auth_middleware import get_current_user, get_current_admin_user, get_optional_current_user
from app.services.food_service import FoodService

router = APIRouter(prefix="/foods", tags=["Foods & Nutrition Catalog"])


async def _attach_favorites(session: AsyncSession, user_id: Optional[str], foods: List[Food]) -> List[FoodOut]:
    fav_ids = set()
    if user_id:
        fav_stmt = select(UserFavoriteFood.food_id).where(UserFavoriteFood.user_id == user_id)
        fav_res = await session.execute(fav_stmt)
        fav_ids = set(fav_res.scalars().all())

    out = []
    for f in foods:
        fo = FoodOut.model_validate(f)
        fo.is_favorite = f.id in fav_ids
        out.append(fo)
    return out


@router.get("", response_model=List[FoodOut])
async def list_foods(
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter category"),
    limit: int = Query(60, ge=1, le=200),
    current_user: Optional[User] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db)
):
    await FoodService.seed_default_foods(session)
    foods = await FoodService.search_foods(session, query or "", category or "", limit=limit)
    user_id = current_user.id if current_user else None
    return await _attach_favorites(session, user_id, foods)


@router.get("/search", response_model=List[FoodOut])
async def search_foods(
    q: Optional[str] = Query(None, description="Search query"),
    query: Optional[str] = Query(None, description="Alternative search query parameter"),
    category: Optional[str] = Query(None, description="Filter category"),
    limit: int = Query(60, ge=1, le=200),
    current_user: Optional[User] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db)
):
    await FoodService.seed_default_foods(session)
    search_term = q or query or ""
    foods = await FoodService.search_foods(session, search_term, category or "", limit=limit)
    user_id = current_user.id if current_user else None
    return await _attach_favorites(session, user_id, foods)


@router.get("/recent", response_model=List[FoodOut])
async def get_recent_foods(
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieves recently tracked foods from user's actual meal history,
    deduplicated and sorted by latest usage.
    """
    await FoodService.seed_default_foods(session)
    
    stmt = (
        select(MealItem, Meal)
        .join(Meal, MealItem.meal_id == Meal.id)
        .where(Meal.user_id == current_user.id)
        .order_by(Meal.occurred_at.desc())
    )
    res = await session.execute(stmt)
    rows = res.all()

    fav_stmt = select(UserFavoriteFood.food_id).where(UserFavoriteFood.user_id == current_user.id)
    fav_res = await session.execute(fav_stmt)
    fav_ids = set(fav_res.scalars().all())

    seen_keys = set()
    recent_foods: List[FoodOut] = []

    for item, meal in rows:
        dedup_key = item.food_id or item.food_name.lower().strip()
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        food_obj = None
        if item.food_id:
            f_stmt = select(Food).where(Food.id == item.food_id).options(selectinload(Food.serving_conversions))
            f_res = await session.execute(f_stmt)
            food_obj = f_res.scalar_one_or_none()

        if not food_obj:
            clean_name = item.food_name.strip()
            f_stmt = select(Food).where(Food.name.ilike(f"%{clean_name}%")).options(selectinload(Food.serving_conversions))
            f_res = await session.execute(f_stmt)
            food_obj = f_res.scalars().first()

        if food_obj:
            food_out = FoodOut.model_validate(food_obj)
            food_out.is_favorite = food_obj.id in fav_ids
            recent_foods.append(food_out)
        else:
            food_out = FoodOut(
                id=item.food_id or item.id,
                name=item.food_name,
                category="Recent Meal",
                serving_size_desc=f"1 {item.serving_unit} (~{item.grams}g)",
                serving_size=item.grams,
                unit="g",
                calories=item.calories,
                protein_g=item.protein_g,
                carbs_g=item.carbs_g,
                fat_g=item.fat_g,
                fiber_g=item.fiber_g,
                sugar_g=item.sugar_g,
                sodium_mg=item.sodium_mg,
                source="User Log",
                updated_at=meal.occurred_at,
                serving_conversions=[],
                is_favorite=False
            )
            recent_foods.append(food_out)

        if len(recent_foods) >= limit:
            break

    return recent_foods


@router.get("/favorites", response_model=List[FoodOut])
async def get_favorite_foods(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieves favorite foods saved by the authenticated user.
    """
    await FoodService.seed_default_foods(session)
    stmt = (
        select(Food)
        .join(UserFavoriteFood, UserFavoriteFood.food_id == Food.id)
        .where(UserFavoriteFood.user_id == current_user.id)
        .options(selectinload(Food.serving_conversions))
        .order_by(UserFavoriteFood.created_at.desc())
    )
    res = await session.execute(stmt)
    foods = res.scalars().all()
    out = []
    for f in foods:
        fo = FoodOut.model_validate(f)
        fo.is_favorite = True
        out.append(fo)
    return out


@router.post("/{food_id}/favorite")
async def add_favorite_food(
    food_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Adds a food item to the user's favorites (per-user storage).
    """
    f_stmt = select(Food).where(Food.id == food_id)
    f_res = await session.execute(f_stmt)
    food = f_res.scalar_one_or_none()
    if not food:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food item not found")

    fav_stmt = select(UserFavoriteFood).where(
        and_(UserFavoriteFood.user_id == current_user.id, UserFavoriteFood.food_id == food_id)
    )
    fav_res = await session.execute(fav_stmt)
    existing_fav = fav_res.scalar_one_or_none()

    if not existing_fav:
        new_fav = UserFavoriteFood(user_id=current_user.id, food_id=food_id)
        session.add(new_fav)
        await session.commit()

    return {"success": True, "food_id": food_id, "is_favorite": True}


@router.delete("/{food_id}/favorite")
async def remove_favorite_food(
    food_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Removes a food item from the user's favorites.
    """
    stmt = select(UserFavoriteFood).where(
        and_(UserFavoriteFood.user_id == current_user.id, UserFavoriteFood.food_id == food_id)
    )
    res = await session.execute(stmt)
    existing_fav = res.scalar_one_or_none()
    if existing_fav:
        await session.delete(existing_fav)
        await session.commit()

    return {"success": True, "food_id": food_id, "is_favorite": False}


@router.get("/barcode/{code}", response_model=FoodOut)
async def get_food_by_barcode(
    code: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db)
):
    await FoodService.seed_default_foods(session)
    stmt = select(Food).where(Food.barcode == code.strip()).options(selectinload(Food.serving_conversions))
    res = await session.execute(stmt)
    food = res.scalar_one_or_none()
    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We couldn't find this packaged food. Try searching the Food Catalog or enter the food manually."
        )
    user_id = current_user.id if current_user else None
    res_list = await _attach_favorites(session, user_id, [food])
    return res_list[0]


@router.get("/{food_id}", response_model=FoodOut)
async def get_food_by_id(
    food_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Food).where(Food.id == food_id).options(selectinload(Food.serving_conversions))
    res = await session.execute(stmt)
    food = res.scalar_one_or_none()
    if not food:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food item not found")
    user_id = current_user.id if current_user else None
    res_list = await _attach_favorites(session, user_id, [food])
    return res_list[0]


@router.post("", response_model=FoodOut, status_code=status.HTTP_201_CREATED)
async def create_food(
    req: FoodCreate,
    admin: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_db)
):
    food = Food(**req.model_dump())
    session.add(food)
    await session.commit()
    await session.refresh(food)
    return food


@router.post("/custom", response_model=CustomFoodOut, status_code=status.HTTP_201_CREATED)
async def create_custom_food(
    req: CustomFoodCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    custom = CustomFood(user_id=current_user.id, **req.model_dump())
    session.add(custom)
    await session.commit()
    await session.refresh(custom)
    return custom
