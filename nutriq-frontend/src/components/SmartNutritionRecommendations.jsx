import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import {
  Sparkles, Flame, Award, Droplets, PlusCircle, CheckCircle2,
  ChevronRight, RefreshCw, AlertCircle, Info, Utensils
} from 'lucide-react';
import { getToday, formatDate } from '../utils/dateUtils';

export const SmartNutritionRecommendations = ({
  targetDate = null,
  mealType = null,
  limit = 4,
  onLogFood = null,
  showHeading = true
}) => {
  const { profile, targets, navigate, isOnline } = useStore();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const selectedDate = targetDate || getToday();

  useEffect(() => {
    fetchRecommendations();
  }, [selectedDate, mealType]);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getSmartRecommendations(selectedDate, mealType, limit);
      setData(res);
    } catch (err) {
      console.warn("Failed to fetch smart recommendations:", err);
      setError("Unable to load smart recommendations.");
    } finally {
      setLoading(false);
    }
  };

  const handleAddFood = (rec) => {
    if (onLogFood) {
      onLogFood(rec);
      return;
    }
    const slot = rec.meal_type || data?.target_meal_type || 'snack';
    const foodName = rec.food_name || rec.name || '';
    navigate(`/log-meal?date=${selectedDate}&meal_type=${slot}&prefill_food=${encodeURIComponent(foodName)}`);
  };

  const getFoodEmoji = (foodName = '', category = '') => {
    const name = foodName.toLowerCase();
    const cat = category.toLowerCase();
    if (name.includes('egg') || name.includes('omelet') || name.includes('anda')) return '🥚';
    if (name.includes('dosa') || name.includes('idli') || name.includes('upma') || name.includes('poha')) return '🥞';
    if (name.includes('paneer') || name.includes('curd') || name.includes('yogurt') || name.includes('lassi')) return '🥛';
    if (name.includes('dal') || name.includes('sambar') || name.includes('rasam') || name.includes('soup')) return '🥣';
    if (name.includes('sprout') || name.includes('salad') || name.includes('cucumber') || name.includes('guava')) return '🥗';
    if (name.includes('chicken') || name.includes('fish') || name.includes('meat')) return '🍗';
    if (name.includes('chapati') || name.includes('roti') || name.includes('paratha')) return '🫓';
    if (name.includes('rice') || name.includes('khichdi') || name.includes('biryani')) return '🍚';
    if (name.includes('banana') || name.includes('apple') || name.includes('fruit')) return '🍌';
    if (name.includes('almond') || name.includes('nut') || name.includes('seed')) return '🥜';
    return '🍽️';
  };

  const recommendations = data?.recommendations || [];
  const remaining = data?.remaining_needs || {
    calories: 0,
    protein_g: 0,
    carbs_g: 0,
    fat_g: 0,
    fiber_g: 0,
    water_l: 0.5
  };
  const gaps = data?.gaps || {};
  const goalDisplay = data?.goal_display || (profile?.fitness_goal ? profile.fitness_goal.replace('_', ' ') : 'Wellness');
  const targetMeal = data?.target_meal_type ? data.target_meal_type.replace('_', ' ').toUpperCase() : 'NEXT MEAL';

  return (
    <div className="wellness-card" style={{ padding: '24px' }}>
      {/* 1. Header */}
      {showHeading && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: 'var(--ai-gradient)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 3px 10px rgba(167, 139, 250, 0.25)'
              }}
            >
              <Sparkles size={18} color="#fff" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                Smart Nutrition Recommendations
              </h3>
              <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                Personalized suggestions based on today's intake and your {goalDisplay} goal.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => navigate('/food-catalog')}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.78rem' }}
          >
            Browse Catalog
          </button>
        </div>
      )}

      {/* 2. Today's Remaining Needs Gap Summary */}
      <div
        style={{
          padding: '14px 18px',
          borderRadius: 'var(--radius-md)',
          background: 'var(--bg-subtle)',
          border: '1px solid var(--border-glass)',
          marginBottom: '18px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
          <span style={{ fontSize: '0.76rem', fontWeight: '800', color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Today's Remaining Needs ({formatDate(selectedDate)})
          </span>
          <span style={{ fontSize: '0.74rem', color: 'var(--primary)', fontWeight: '700' }}>
            Tailored for {targetMeal}
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px' }}>
          <div style={{ background: 'var(--bg-card)', padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-glass)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--calorie-orange)', fontSize: '0.72rem', fontWeight: '700' }}>
              <Flame size={14} /> Calories Needed
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
              {Math.round(remaining.calories || 0)} <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>kcal</span>
            </div>
          </div>

          <div style={{ background: 'var(--bg-card)', padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-glass)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--macro-protein)', fontSize: '0.72rem', fontWeight: '700' }}>
              <Award size={14} /> Protein Needed
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
              {Math.round(remaining.protein_g || 0)} <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>g</span>
              {gaps.protein === 'HIGH' && (
                <span className="badge badge-rose" style={{ marginLeft: '6px', fontSize: '0.65rem' }}>
                  High Priority
                </span>
              )}
            </div>
          </div>

          <div style={{ background: 'var(--bg-card)', padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-glass)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--macro-fiber)', fontSize: '0.72rem', fontWeight: '700' }}>
              🥗 Fiber Needed
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
              {Math.round(remaining.fiber_g || 0)} <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>g</span>
            </div>
          </div>

          <div style={{ background: 'var(--bg-card)', padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-glass)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--hydration-cyan)', fontSize: '0.72rem', fontWeight: '700' }}>
              <Droplets size={14} /> Hydration Needed
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
              {(remaining.water_l || 0).toFixed(1)} <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>L</span>
            </div>
          </div>
        </div>

        {/* Intelligent Nutrition Goal Alerts */}
        {Array.isArray(data?.warnings) && data.warnings.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px' }}>
            {data.warnings.map((w, wIdx) => (
              <div
                key={wIdx}
                style={{
                  background: w.type === 'calories_exceeded' || w.type === 'carbs_exceeded' ? 'var(--warning-bg)' : 'var(--success-bg)',
                  border: `1px solid ${w.type === 'calories_exceeded' || w.type === 'carbs_exceeded' ? 'rgba(245, 158, 11, 0.25)' : 'rgba(8, 127, 91, 0.25)'}`,
                  borderRadius: 'var(--radius-sm)',
                  padding: '8px 12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '0.8rem',
                  color: 'var(--text-primary)'
                }}
              >
                <AlertCircle size={15} color={w.type === 'calories_exceeded' || w.type === 'carbs_exceeded' ? 'var(--warning)' : 'var(--primary)'} style={{ flexShrink: 0 }} />
                <span><strong>{w.title}:</strong> {w.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 3. Recommendations State */}
      {loading ? (
        <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <RefreshCw size={20} className="spin" style={{ margin: '0 auto 8px auto', color: 'var(--primary)' }} />
          <div>Generating personalized nutrition recommendations...</div>
        </div>
      ) : error ? (
        <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <p style={{ margin: 0, fontSize: '0.88rem' }}>{error}</p>
          <button
            type="button"
            onClick={fetchRecommendations}
            className="btn-secondary"
            style={{ marginTop: '10px', padding: '5px 12px', fontSize: '0.78rem' }}
          >
            Retry
          </button>
        </div>
      ) : recommendations.length === 0 ? (
        <div style={{ padding: '28px', textAlign: 'center', color: 'var(--text-secondary)', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
          <Info size={24} color="var(--primary)" style={{ margin: '0 auto 8px auto' }} />
          <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-primary)', fontWeight: '700' }}>
            {data?.message || "Start logging your meals to receive dynamically tailored food suggestions."}
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px' }}>
          {recommendations.map((rec, idx) => {
            const foodName = rec.food_name || rec.name || 'Food Item';
            const emoji = getFoodEmoji(foodName, rec.category);
            const cal = Math.round(rec.calories || 0);
            const pro = Math.round((rec.protein_g || rec.protein || 0) * 10) / 10;
            const carb = Math.round((rec.carbs_g || rec.carbs || 0) * 10) / 10;
            const fat = Math.round((rec.fat_g || rec.fat || 0) * 10) / 10;
            const fib = Math.round((rec.fiber_g || rec.fiber || 0) * 10) / 10;
            const matchScore = rec.suitability_score || rec.score ? Math.round((rec.suitability_score || rec.score) * 100) : null;
            const tags = Array.isArray(rec.dietary_tags) ? rec.dietary_tags : [];
            const portionLabel = `${rec.serving_quantity || 1} ${rec.serving_unit || 'serving'} (~${Math.round(rec.grams || 100)}g)`;

            return (
              <div
                key={rec.food_id || idx}
                style={{
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border-glass)',
                  padding: '16px 18px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '12px',
                  transition: 'all 0.16s ease'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'var(--primary)';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'var(--border-glass)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                {/* Header: Emojis, Name & Badges */}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', flexWrap: 'wrap', gap: '4px' }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      {rec.category || 'General'} · {(rec.meal_type || 'meal').toUpperCase()}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap' }}>
                      {matchScore && (
                        <span className="badge badge-emerald" style={{ fontSize: '0.66rem', padding: '1px 6px' }}>
                          <Sparkles size={10} style={{ marginRight: '3px' }} /> {matchScore}% Match
                        </span>
                      )}
                      {tags.slice(0, 2).map((t, tIdx) => (
                        <span key={tIdx} className="badge badge-subtle" style={{ fontSize: '0.64rem', padding: '1px 5px' }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '1.25rem' }}>{emoji}</span>
                    <h4 style={{ fontSize: '1rem', fontWeight: '800', color: 'var(--text-primary)', margin: 0, lineHeight: '1.3' }}>
                      {foodName}
                    </h4>
                  </div>

                  <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                    Portion: <strong style={{ color: 'var(--primary)' }}>{portionLabel}</strong>
                  </div>
                </div>

                {/* Reason Explanation */}
                {rec.reason && (
                  <div
                    style={{
                      padding: '8px 10px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--ai-violet-light)',
                      border: '1px solid var(--ai-border)',
                      fontSize: '0.78rem',
                      color: 'var(--text-secondary)',
                      lineHeight: '1.4'
                    }}
                  >
                    "{rec.reason}"
                  </div>
                )}

                {/* Macro Pill Grid */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: '4px',
                    textAlign: 'center',
                    padding: '8px 6px',
                    background: 'var(--bg-card)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-glass)'
                  }}
                >
                  <div>
                    <span style={{ fontSize: '0.64rem', color: 'var(--text-muted)', display: 'block' }}>Calories</span>
                    <strong style={{ fontSize: '0.84rem', color: 'var(--calorie-orange)' }}>{cal}</strong>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.64rem', color: 'var(--text-muted)', display: 'block' }}>Protein</span>
                    <strong style={{ fontSize: '0.84rem', color: 'var(--macro-protein)' }}>{pro}g</strong>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.64rem', color: 'var(--text-muted)', display: 'block' }}>Carbs</span>
                    <strong style={{ fontSize: '0.84rem', color: 'var(--text-primary)' }}>{carb}g</strong>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.64rem', color: 'var(--text-muted)', display: 'block' }}>Fiber</span>
                    <strong style={{ fontSize: '0.84rem', color: 'var(--macro-fiber)' }}>{fib}g</strong>
                  </div>
                </div>

                {/* Add to Meal Action Button */}
                <button
                  type="button"
                  onClick={() => handleAddFood(rec)}
                  className="btn-secondary"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    fontSize: '0.82rem',
                    fontWeight: '700',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    color: 'var(--primary)',
                    borderColor: 'var(--primary)'
                  }}
                  title={`Log ${foodName} to ${rec.meal_type || 'meal'}`}
                >
                  <PlusCircle size={15} /> Add to Meal
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default SmartNutritionRecommendations;
