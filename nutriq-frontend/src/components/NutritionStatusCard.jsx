import React from 'react';
import { useStore } from '../store/useStore';
import {
  CheckCircle2, AlertTriangle, AlertCircle, TrendingUp, Flame,
  Award, ArrowRight, Sparkles, Info, Activity
} from 'lucide-react';
import { calculateCalorieStatus } from '../utils/calorieStatus';

export const NutritionStatusCard = ({ statusData, onNavigateSummary }) => {
  const { navigate } = useStore();

  if (!statusData) return null;

  const {
    goal_display = 'Weight Loss',
    goal = 'weight_loss',
    daily_calorie_target = 2000,
    calories_consumed = 0,
    calories_burned = 0,
    calories_remaining = 2000,
    calorie_difference = 0,
    status_level,
    status_badge,
    calorie_status,
    warning_title,
    warning_message,
    positive_feedback,
    has_meals_logged = false
  } = statusData;

  // Use centralized calculation if available or fallback
  const calStatus = calorie_status || calculateCalorieStatus({
    targetCalories: daily_calorie_target,
    consumedCalories: calories_consumed,
    burnedCalories: calories_burned,
    goalType: goal,
    hasMeals: has_meals_logged || calories_consumed > 0
  });

  const effectiveStatus = calStatus.statusLevel || status_level || 'on_track';
  const effectiveBadge = calStatus.statusBadge || status_badge || 'On Track';

  // Determine theme colors and icon based on effectiveStatus
  let badgeColor = 'badge-emerald';
  let icon = <CheckCircle2 size={18} color="#10b981" />;
  let borderStyle = 'rgba(16, 185, 129, 0.25)';

  if (effectiveStatus === 'very_low') {
    badgeColor = 'badge-rose';
    icon = <AlertCircle size={18} color="#f43f5e" />;
    borderStyle = 'rgba(244, 63, 94, 0.35)';
  } else if (effectiveStatus === 'below_target') {
    badgeColor = 'badge-amber';
    icon = <Info size={18} color="#f59e0b" />;
    borderStyle = 'rgba(245, 158, 11, 0.3)';
  } else if (effectiveStatus === 'target_exceeded' || effectiveStatus === 'slightly_above' || effectiveStatus === 'significantly_above') {
    badgeColor = 'badge-rose';
    icon = <AlertTriangle size={18} color="#f97316" />;
    borderStyle = 'rgba(249, 115, 22, 0.35)';
  } else if (effectiveStatus === 'no_meals') {
    badgeColor = 'badge-gray';
    icon = <Info size={18} color="var(--text-muted)" />;
    borderStyle = 'rgba(255, 255, 255, 0.1)';
  }

  const handleCardClick = () => {
    if (onNavigateSummary) {
      onNavigateSummary();
    } else {
      navigate('/daily-summary');
    }
  };

  const remainingKcal = Math.max(0, Math.round(daily_calorie_target - calories_consumed));

  return (
    <div
      onClick={handleCardClick}
      className="glass-panel"
      style={{
        padding: '20px',
        border: `1px solid ${borderStyle}`,
        cursor: 'pointer',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}
      title="Click to view detailed Daily Summary"
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {icon}
          <span style={{ fontSize: '0.82rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>
            Goal Status ({goal_display})
          </span>
        </div>
        <span className={`badge ${badgeColor}`} style={{ fontSize: '0.75rem', fontWeight: '700' }}>
          {effectiveBadge}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
        <div>
          <span style={{ fontSize: '1.45rem', fontWeight: '800', color: 'var(--text-primary)' }}>
            {Math.round(calories_consumed).toLocaleString()}
          </span>
          <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
            {' '}/ {Math.round(daily_calorie_target).toLocaleString()} kcal food consumed
          </span>
        </div>
        <div style={{ fontSize: '0.85rem', fontWeight: '700', color: remainingKcal > 0 ? '#38bdf8' : '#f97316' }}>
          {remainingKcal > 0 ? `${remainingKcal.toLocaleString()} kcal left` : 'Target met'}
        </div>
      </div>

      {calories_burned > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: '#06b6d4' }}>
          <Activity size={14} />
          <span>Exercise burned: <strong>{Math.round(calories_burned).toLocaleString()} kcal</strong></span>
        </div>
      )}

      <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
        {calStatus.message || warning_message || positive_feedback || (has_meals_logged ? "Tracking active." : "Start logging your meals today.")}
      </p>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px', fontSize: '0.78rem', color: '#34d399', fontWeight: '600', marginTop: '2px' }}>
        <span>View full breakdown</span>
        <ArrowRight size={13} />
      </div>
    </div>
  );
};
