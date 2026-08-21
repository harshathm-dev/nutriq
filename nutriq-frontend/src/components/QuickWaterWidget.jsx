import React from 'react';
import { Droplet, Plus } from 'lucide-react';
import { api } from '../services/api';
import { useStore } from '../store/useStore';

export const QuickWaterWidget = ({ consumedMl = 0, targetMl = 2500 }) => {
  const { refreshAllData } = useStore();
  const pct = Math.min(100, Math.round((consumedMl / Math.max(1, targetMl)) * 100));

  const handleAddWater = async (amount) => {
    await api.logWater(amount);
    await refreshAllData();
  };

  return (
    <div className="glass-panel" style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ padding: '6px', borderRadius: '8px', background: 'var(--water-badge, #E6FFFA)', color: 'var(--water, #0D9488)' }}>
            <Droplet size={18} />
          </div>
          <div>
            <div style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-primary)' }}>Daily Hydration</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {consumedMl} ml / {targetMl} ml ({pct}%)
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => handleAddWater(250)}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.78rem', borderRadius: '8px' }}
          >
            +250ml
          </button>
          <button
            onClick={() => handleAddWater(500)}
            className="btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.78rem', borderRadius: '8px' }}
          >
            +500ml
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div style={{ width: '100%', height: '8px', background: 'var(--border-glass-light, #EBF2EE)', borderRadius: '4px', overflow: 'hidden' }}>
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            background: 'var(--hydration-gradient, linear-gradient(90deg, #0D9488, #0F766E))',
            borderRadius: '4px',
            transition: 'width 0.5s ease'
          }}
        />
      </div>
    </div>
  );
};
