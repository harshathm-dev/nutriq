import React from 'react';
import { AlertTriangle, Info, AlertOctagon, X } from 'lucide-react';

export const SmartWarningBanner = ({ warnings = [] }) => {
  if (!warnings || warnings.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
      {warnings.map((w, index) => {
        const isHigh = w.severity === 'high';
        const Icon = isHigh ? AlertOctagon : (w.severity === 'medium' ? AlertTriangle : Info);
        const bg = isHigh
          ? 'linear-gradient(135deg, rgba(244, 63, 94, 0.15), rgba(159, 18, 57, 0.25))'
          : 'linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(180, 83, 9, 0.25))';
        const borderColor = isHigh ? 'rgba(244, 63, 94, 0.4)' : 'rgba(245, 158, 11, 0.4)';
        const textColor = isHigh ? '#fb7185' : '#fbbf24';

        return (
          <div
            key={index}
            className="glass-panel pulse-active"
            style={{
              background: bg,
              borderColor: borderColor,
              padding: '14px 18px',
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'space-between',
              gap: '12px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <div style={{ padding: '4px', color: textColor }}>
                <Icon size={20} />
              </div>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.04em', color: textColor, marginBottom: '2px' }}>
                  Smart Warning • {w.type?.replace('_', ' ')}
                </div>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                  {w.message}
                </div>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.currentTarget.parentElement.style.display = 'none';
              }}
              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
            >
              <X size={16} />
            </button>
          </div>
        );
      })}
    </div>
  );
};
