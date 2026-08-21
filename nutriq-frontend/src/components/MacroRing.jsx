import React from 'react';

export const MacroRing = ({
  label,
  current = 0,
  target = 100,
  unit = 'g',
  color = '#3b82f6',
  gradientId,
  size = 90,
  strokeWidth = 8
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const safeTarget = Math.max(1, target || 1);
  const safeCurrent = Math.max(0, current || 0);
  const pct = Math.min(100, Math.max(0, (safeCurrent / safeTarget) * 100));
  const strokeDashoffset = circumference - (pct / 100) * circumference;
  const gId = gradientId || `macro-grad-${label.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
      <div style={{ position: 'relative', width: size, height: size, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          <defs>
            <linearGradient id={gId} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={color} stopOpacity="1" />
              <stop offset="100%" stopColor={color} stopOpacity="0.75" />
            </linearGradient>
            <filter id={`glow-${gId}`} x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="2" floodColor={color} floodOpacity="0.4" />
            </filter>
          </defs>

          {/* Track circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="rgba(255, 255, 255, 0.07)"
            strokeWidth={strokeWidth}
            fill="transparent"
          />

          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={`url(#${gId})`}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            filter={`url(#glow-${gId})`}
            style={{ transition: 'stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1)' }}
          />
        </svg>

        <div style={{ position: 'absolute', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <span style={{ fontSize: '0.88rem', fontWeight: '800', color: 'var(--text-primary)', lineHeight: 1.1 }}>
            {Math.round(safeCurrent)}
          </span>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontWeight: '600' }}>
            /{Math.round(safeTarget)}{unit}
          </span>
        </div>
      </div>

      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: '700', color: color, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          {label}
        </div>
        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: '500' }}>
          {Math.round(pct)}%
        </div>
      </div>
    </div>
  );
};
