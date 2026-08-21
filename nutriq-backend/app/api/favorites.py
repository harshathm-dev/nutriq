import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.database.session import get_db
from app.models.user import User
from app.models.meal import FavoriteMeal, Recipe, RecipeIngredient
from app.schemas.meal import (
    FavoriteMealCreate, FavoriteMealOut,
    RecipeCreate, RecipeOut, RecipeIngredientOut
)
from app.middleware.auth_middleware import get_current_user

router = APIRouter(tags=["Favorites & Meal Templates"])

@router.get("/favorites", response_model=List[FavoriteMealOut])
async def list_favorites(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(FavoriteMeal).where(FavoriteMeal.user_id == current_user.id).order_by(FavoriteMeal.created_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())

@router.post("/favorites", response_model=FavoriteMealOut, status_code=status.HTTP_201_CREATED)
async def create_favorite(
    req: FavoriteMealCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    payload = json.dumps([item.model_dump() for item in req.items])
    fav = FavoriteMeal(
        user_id=current_user.id,
        name=req.name,
        meal_type=req.meal_type,
        template_payload=payload
    )
    session.add(fav)
    await session.commit()
    await session.refresh(fav)
    return fav

@router.get("/recipes", response_model=List[RecipeOut])
async def list_recipes(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    stmt = select(Recipe).where(Recipe.user_id == current_user.id).options(selectinload(Recipe.ingredients)).order_by(Recipe.created_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())

@router.post("/recipes", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
async def create_recipe(
    req: RecipeCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    recipe = Recipe(
        user_id=current_user.id,
        name=req.name,
        description=req.description or "",
        servings=req.servings,
        total_calories=0.0,
        total_protein_g=0.0,
        total_carbs_g=0.0,
        total_fat_g=0.0
    )
    session.add(recipe)
    await session.flush()

    for ing in req.ingredients:
        item = RecipeIngredient(
            recipe_id=recipe.id,
            food_id=ing.food_id,
            food_name=ing.food_name,
            quantity=ing.quantity,
            unit=ing.unit,
            grams=ing.grams
        )
        session.add(item)

    await session.commit()
    stmt = select(Recipe).where(Recipe.id == recipe.id).options(selectinload(Recipe.ingredients))
    res = await session.execute(stmt)
    return res.scalar_one()
