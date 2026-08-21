import React from 'react';
import { useStore } from '../store/useStore';
import {
  Sparkles, PlusCircle, Flame, Award, Tag, Utensils, Check, ArrowRight
} from 'lucide-react';

export const FoodRecommendationCard = ({ recommendation, onLogFood }) => {
  const { navigate } = useStore();

  if (!recommendation) return null;

  const {
    food_id,
    food_name,
    category = 'General',
    serving_quantity = 1,
    serving_unit = 'serving',
    grams = 100,
    calories = 0,
    protein_g = 0,
    carbs_g = 0,
    fat_g = 0,
    fiber_g = 0,
    meal_type = 'snack',
    reason,
    suitability_score,
    recommendation_source = 'ml_model',
    dietary_tags = []
  } = recommendation;

  const matchPercent = suitability_score ? Math.round(suitability_score * 100) : null;

  const handleLogClick = () => {
    if (onLogFood) {
      onLogFood(recommendation);
    } else {
      navigate(`/log-meal?meal_type=${meal_type}&prefill_food=${encodeURIComponent(food_name)}`);
    }
  };

  return (
    <div
      className="glass-panel"
      style={{
        padding: '16px 18px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '12px',
        border: '1px solid var(--border-glass)',
        borderRadius: 'var(--radius-md)',
        background: 'var(--bg-glass)',
        transition: 'transform 0.2s ease, border-color 0.2s ease'
      }}
    >
      {/* Top Title & Category */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', flexWrap: 'wrap', gap: '4px' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {category} · {meal_type.toUpperCase()}
          </span>
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
            {matchPercent !== null && (
              <span className="badge badge-purple" style={{ fontSize: '0.68rem', padding: '2px 7px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Sparkles size={11} /> {matchPercent}% Match
              </span>
            )}
            {dietary_tags.map((tag, idx) => (
              <span key={idx} className="badge badge-emerald" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                {tag}
              </span>
            ))}
          </div>
        </div>

        <h4 style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-primary)', margin: '0 0 4px 0' }}>
          {food_name}
        </h4>

        {/* Portion Display */}
        <div style={{ fontSize: '0.82rem', color: '#34d399', fontWeight: '600' }}>
          Portion: {serving_quantity} {serving_unit} ({Math.round(grams)} g)
        </div>
      </div>

      {/* Reason / Context */}
      {reason && (
        <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: '1.35' }}>
          {reason}
        </p>
      )}

      {/* Macros Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', textAlign: 'center', background: 'rgba(15, 23, 42, 0.4)', padding: '8px', borderRadius: '6px' }}>
        <div>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Calories</span>
          <div style={{ fontSize: '0.88rem', fontWeight: '700', color: '#f59e0b' }}>{Math.round(calories)}</div>
        </div>
        <div>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Protein</span>
          <div style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--macro-protein)' }}>{protein_g}g</div>
        </div>
        <div>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Carbs</span>
          <div style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--macro-carbs)' }}>{carbs_g}g</div>
        </div>
        <div>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Fiber</span>
          <div style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--macro-fiber)' }}>{fiber_g}g</div>
        </div>
      </div>

      {/* Log Button */}
      <button
        onClick={handleLogClick}
        className="btn-secondary"
        style={{
          width: '100%',
          padding: '7px 12px',
          fontSize: '0.8rem',
          fontWeight: '700',
          justifyContent: 'center',
          gap: '6px',
          color: '#34d399',
          border: '1px solid rgba(52, 211, 153, 0.3)'
        }}
      >
        <PlusCircle size={14} />
        <span>Log This Food</span>
      </button>
    </div>
  );
};
