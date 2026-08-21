import React from 'react';
import {
  CheckCircle2, AlertTriangle, AlertCircle, TrendingUp, Award,
  Info, Sparkles, Calendar
} from 'lucide-react';

export const NutritionWarning = ({ statusData }) => {
  if (!statusData) return null;

  const {
    status_level = 'on_track',
    status_badge = 'On Track',
    warning_title,
    warning_message,
    why_it_matters,
    positive_feedback,
    weekly_pattern_warning,
    goal_display = 'Weight Loss'
  } = statusData;

  // Visual Theme Setup
  let bgColor = 'rgba(16, 185, 129, 0.08)';
  let borderColor = 'rgba(16, 185, 129, 0.25)';
  let textColor = '#34d399';
  let icon = <CheckCircle2 size={22} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />;

  if (status_level === 'near_target') {
    bgColor = 'rgba(245, 158, 11, 0.08)';
    borderColor = 'rgba(245, 158, 11, 0.25)';
    textColor = '#fbbf24';
    icon = <Info size={22} color="#f59e0b" style={{ flexShrink: 0, marginTop: '2px' }} />;
  } else if (status_level === 'slightly_above') {
    bgColor = 'rgba(245, 158, 11, 0.12)';
    borderColor = 'rgba(245, 158, 11, 0.35)';
    textColor = '#fbbf24';
    icon = <AlertTriangle size={22} color="#f59e0b" style={{ flexShrink: 0, marginTop: '2px' }} />;
  } else if (status_level === 'significantly_above') {
    bgColor = 'rgba(244, 63, 94, 0.12)';
    borderColor = 'rgba(244, 63, 94, 0.35)';
    textColor = '#fb7185';
    icon = <AlertCircle size={22} color="#f43f5e" style={{ flexShrink: 0, marginTop: '2px' }} />;
  } else if (status_level === 'below_target') {
    bgColor = 'rgba(56, 189, 248, 0.08)';
    borderColor = 'rgba(56, 189, 248, 0.25)';
    textColor = '#38bdf8';
    icon = <TrendingUp size={22} color="#38bdf8" style={{ flexShrink: 0, marginTop: '2px' }} />;
  } else if (status_level === 'protein_low') {
    bgColor = 'rgba(167, 139, 250, 0.08)';
    borderColor = 'rgba(167, 139, 250, 0.25)';
    textColor = '#a78bfa';
    icon = <Award size={22} color="#a78bfa" style={{ flexShrink: 0, marginTop: '2px' }} />;
  }

  const primaryMessage = warning_message || positive_feedback;
  if (!primaryMessage && !weekly_pattern_warning) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Primary Goal Warning / Positive Feedback Card */}
      {primaryMessage && (
        <div
          style={{
            padding: '18px 20px',
            borderRadius: 'var(--radius-md)',
            background: bgColor,
            border: `1px solid ${borderColor}`,
            display: 'flex',
            alignItems: 'flex-start',
            gap: '14px'
          }}
        >
          {icon}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.95rem', fontWeight: '800', color: textColor }}>
                {warning_title || status_badge}
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                ({goal_display})
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-primary)', lineHeight: '1.45' }}>
              {primaryMessage}
            </p>
            {why_it_matters && (
              <div style={{ marginTop: '4px', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                <strong style={{ color: 'var(--text-muted)' }}>Why this matters: </strong>
                {why_it_matters}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Weekly Pattern Warning Alert */}
      {weekly_pattern_warning && (
        <div
          style={{
            padding: '14px 18px',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.25)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            fontSize: '0.86rem',
            color: 'var(--text-primary)'
          }}
        >
          <Calendar size={18} color="#f59e0b" style={{ flexShrink: 0 }} />
          <div>
            <strong style={{ color: '#fbbf24' }}>Weekly Trend Note: </strong>
            {weekly_pattern_warning}
          </div>
        </div>
      )}
    </div>
  );
};
