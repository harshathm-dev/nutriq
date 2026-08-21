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
  let bgColor = 'var(--success-bg)';
  let borderColor = 'rgba(8, 127, 91, 0.25)';
  let textColor = 'var(--success)';
  let icon = <CheckCircle2 size={22} color="var(--success)" style={{ flexShrink: 0, marginTop: '2px' }} />;

  if (status_level === 'near_target') {
    bgColor = 'var(--warning-bg)';
    borderColor = 'rgba(245, 158, 11, 0.25)';
    textColor = 'var(--warning)';
    icon = <Info size={22} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />;
  } else if (status_level === 'slightly_above') {
    bgColor = 'var(--warning-bg)';
    borderColor = 'rgba(245, 158, 11, 0.35)';
    textColor = 'var(--warning)';
    icon = <AlertTriangle size={22} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />;
  } else if (status_level === 'significantly_above') {
    bgColor = 'var(--error-bg)';
    borderColor = 'rgba(239, 68, 68, 0.35)';
    textColor = 'var(--error)';
    icon = <AlertCircle size={22} color="var(--error)" style={{ flexShrink: 0, marginTop: '2px' }} />;
  } else if (status_level === 'below_target') {
    bgColor = 'var(--macro-protein-light)';
    borderColor = 'rgba(37, 99, 235, 0.25)';
    textColor = 'var(--macro-protein)';
    icon = <TrendingUp size={22} color="var(--macro-protein)" style={{ flexShrink: 0, marginTop: '2px' }} />;
  } else if (status_level === 'protein_low') {
    bgColor = 'var(--warning-bg)';
    borderColor = 'rgba(245, 158, 11, 0.25)';
    textColor = 'var(--warning)';
    icon = <Award size={22} color="var(--warning)" style={{ flexShrink: 0, marginTop: '2px' }} />;
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
