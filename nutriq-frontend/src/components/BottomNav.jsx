import React from 'react';
import { useStore } from '../store/useStore';
import { LayoutDashboard, PlusCircle, History, CalendarDays, Sparkles } from 'lucide-react';

export const BottomNav = () => {
  const { activeTab, setTab } = useStore();

  const items = [
    { id: 'dashboard', label: 'Today', icon: LayoutDashboard },
    { id: 'meal_history', label: 'History', icon: History },
    { id: 'add_food', label: 'Log Meal', icon: PlusCircle, isPrimary: true },
    { id: 'planner', label: 'Planner', icon: CalendarDays },
    { id: 'assistant', label: 'NutriQ AI', icon: Sparkles }
  ];

  return (
    <div
      className="wellness-card"
      id="nutriq-bottom-nav"
      style={{
        display: 'none',
        position: 'fixed',
        bottom: '12px',
        left: '12px',
        right: '12px',
        height: '62px',
        zIndex: 999,
        padding: '0 8px',
        alignItems: 'center',
        justifyContent: 'space-around',
        borderRadius: 'var(--radius-full)',
        background: 'var(--bg-glass)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid var(--border-glass)',
        boxShadow: 'var(--shadow-lg)'
      }}
    >
      <style>{`
        @media (max-width: 840px) {
          #nutriq-bottom-nav {
            display: flex !important;
          }
        }
      `}</style>
      {items.map(item => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;

        if (item.isPrimary) {
          return (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                background: 'var(--primary-gradient)',
                border: 'none',
                color: '#FFFFFF',
                cursor: 'pointer',
                boxShadow: '0 4px 12px rgba(8, 127, 91, 0.35)',
                transform: 'translateY(-8px)',
                transition: 'all 0.2s ease'
              }}
              title={item.label}
            >
              <Icon size={24} color="#FFFFFF" />
            </button>
          );
        }

        return (
          <button
            key={item.id}
            onClick={() => setTab(item.id)}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '2px',
              background: 'transparent',
              border: 'none',
              color: isActive ? 'var(--primary)' : 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px 10px',
              borderRadius: 'var(--radius-md)',
              transition: 'all 0.15s ease'
            }}
          >
            <Icon size={19} color={isActive ? 'var(--primary)' : 'var(--text-muted)'} />
            <span style={{ fontSize: '0.68rem', fontWeight: isActive ? '700' : '600' }}>
              {item.label}
            </span>
          </button>
        );
      })}
    </div>
  );
};
