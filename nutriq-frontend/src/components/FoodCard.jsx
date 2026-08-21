import React, { useState } from 'react';
import { Heart, Plus, Check } from 'lucide-react';
import { api } from '../services/api';

export const FoodCard = ({
  food,
  onAddFood,
  onSelectFood,
  isSelected = false,
  compact = false
}) => {
  const [isFavorite, setIsFavorite] = useState(Boolean(food.is_favorite));
  const [favoriteLoading, setFavoriteLoading] = useState(false);
  const [justAdded, setJustAdded] = useState(false);

  const handleFavoriteClick = async (e) => {
    e.stopPropagation();
    if (favoriteLoading) return;
    setFavoriteLoading(true);
    const nextState = !isFavorite;
    setIsFavorite(nextState);

    try {
      await api.toggleFavoriteFood(food.id || food.food_id, isFavorite);
    } catch (err) {
      console.warn("Failed to toggle favorite:", err);
      setIsFavorite(!nextState); // Rollback on failure
    } finally {
      setFavoriteLoading(false);
    }
  };

  const handleAddClick = (e) => {
    e.stopPropagation();
    if (onAddFood) {
      onAddFood(food);
      setJustAdded(true);
      setTimeout(() => setJustAdded(false), 1200);
    }
  };

  const calories = Math.round(food.calories || 0);
  const protein = Math.round(food.protein || food.protein_g || 0);
  const carbs = Math.round(food.carbs || food.carbs_g || 0);
  const fat = Math.round(food.fat || food.fat_g || 0);
  const fiber = Math.round(food.fiber || food.fiber_g || 0);
  const servingDesc = food.serving_size_desc || food.serving_size || '1 serving (100g)';

  return (
    <div
      className="wellness-card wellness-card-interactive"
      onClick={() => onSelectFood && onSelectFood(food)}
      style={{
        padding: compact ? '12px 14px' : '16px 18px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '12px',
        borderColor: isSelected ? 'var(--primary)' : 'var(--border-glass)',
        background: isSelected ? 'var(--primary-light)' : 'var(--bg-card)'
      }}
    >
      {/* Top Header: Name, Category, Favorite Icon */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px' }}>
        <div>
          <h4 style={{ fontSize: compact ? '0.92rem' : '1.02rem', fontWeight: '800', color: 'var(--text-primary)', margin: 0 }}>
            {food.name}
          </h4>
          <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
            {servingDesc}
          </span>
        </div>

        <button
          type="button"
          onClick={handleFavoriteClick}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: '4px',
            color: isFavorite ? 'var(--calorie-orange, #FF6B4A)' : 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'transform 0.15s ease'
          }}
          title={isFavorite ? "Remove from Favorites" : "Add to Favorites"}
        >
          <Heart size={18} fill={isFavorite ? "var(--calorie-orange, #FF6B4A)" : "none"} />
        </button>
      </div>

      {/* Macros & Energy Badges */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <span style={{ fontSize: '1.05rem', fontWeight: '800', color: 'var(--calorie-orange)' }}>
            {calories} <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: '600' }}>kcal</span>
          </span>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            P: {protein}g • C: {carbs}g • F: {fat}g {fiber > 0 ? `• Fib: ${fiber}g` : ''}
          </div>
        </div>

        {/* Quick Add Button */}
        {onAddFood && (
          <button
            type="button"
            onClick={handleAddClick}
            className={justAdded ? "btn-secondary" : "btn-primary"}
            style={{
              padding: '6px 12px',
              fontSize: '0.78rem',
              gap: '4px',
              borderRadius: 'var(--radius-md)'
            }}
          >
            {justAdded ? (
              <>
                <Check size={14} color="var(--primary)" /> Added
              </>
            ) : (
              <>
                <Plus size={14} /> Add
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};
