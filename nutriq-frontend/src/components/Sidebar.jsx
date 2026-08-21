import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { WaterModal } from './WaterModal';
import { ActivityModal } from './ActivityModal';
import {
  LayoutDashboard, PlusCircle, History, Droplets, Dumbbell,
  CalendarDays, Target, FileText, BarChart3, Search, Heart,
  Sparkles, ShieldCheck, Settings, ChevronLeft, ChevronRight
} from 'lucide-react';

export const Sidebar = () => {
  const { activeTab, setTab, navigate } = useStore();
  const [collapsed, setCollapsed] = useState(false);
  const [showWaterModal, setShowWaterModal] = useState(false);
  const [showActivityModal, setShowActivityModal] = useState(false);

  const navGroups = [
    {
      label: 'Main',
      items: [
        { id: 'dashboard', label: 'Overview', icon: LayoutDashboard }
      ]
    },
    {
      label: 'Track',
      items: [
        { id: 'add_food', label: 'Log Meal', icon: PlusCircle },
        { id: 'meal_history', label: 'Meal History', icon: History },
        { id: 'activity_history', label: 'Activity History', icon: Dumbbell },
        { id: 'water_quick', label: 'Water Intake', icon: Droplets, isModal: 'water' }
      ]
    },
    {
      label: 'Plan',
      items: [
        { id: 'planner', label: 'Meal Planner', icon: CalendarDays }
      ]
    },
    {
      label: 'Insights',
      items: [
        { id: 'daily_summary', label: 'Daily Summary', icon: FileText },
        { id: 'weekly_summary', label: 'Weekly Summary', icon: FileText },
        { id: 'analytics', label: 'Analytics', icon: BarChart3 }
      ]
    },
    {
      label: 'Discover',
      items: [
        { id: 'search', label: 'Food Catalog', icon: Search }
      ]
    },
    {
      label: 'AI Intelligence',
      items: [
        { id: 'assistant', label: 'NutriQ AI', icon: Sparkles, isAi: true }
      ]
    },
    {
      label: 'Account',
      items: [
        { id: 'privacy', label: 'Privacy & Data', icon: ShieldCheck },
        { id: 'settings', label: 'Settings', icon: Settings }
      ]
    }
  ];

  const handleItemClick = (item) => {
    if (item.isModal === 'water') {
      setShowWaterModal(true);
    } else if (item.isModal === 'activity') {
      setShowActivityModal(true);
    } else {
      setTab(item.id);
    }
  };

  return (
    <>
      <aside
        className="wellness-card"
        id="nutriq-sidebar"
        style={{
          width: collapsed ? '76px' : '260px',
          margin: '16px 0 16px 24px',
          padding: collapsed ? '16px 8px' : '18px 12px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          height: 'calc(100vh - 100px)',
          position: 'sticky',
          top: '90px',
          transition: 'width 0.22s cubic-bezier(0.16, 1, 0.3, 1)',
          overflowY: 'auto',
          zIndex: 30
        }}
      >
        <style>{`
          @media (max-width: 840px) {
            #nutriq-sidebar {
              display: none !important;
            }
          }
        `}</style>

        {/* Navigation Groups */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {navGroups.map((grp, gIdx) => (
            <div key={gIdx} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {!collapsed && grp.label && (
                <div style={{
                  padding: '2px 12px 4px 12px',
                  fontSize: '0.68rem',
                  fontWeight: '800',
                  color: 'var(--text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em'
                }}>
                  {grp.label}
                </div>
              )}

              {grp.items.map(item => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;

                let activeBg = 'var(--sidebar-active-bg, var(--primary-light))';
                let activeColor = 'var(--sidebar-active-text, var(--primary-dark))';
                let iconColor = isActive ? 'var(--sidebar-active-icon, var(--primary))' : 'var(--sidebar-icon, var(--text-secondary))';

                if (item.isAi) {
                  if (isActive) {
                    activeBg = 'var(--ai-violet-light)';
                    activeColor = 'var(--ai-violet)';
                    iconColor = 'var(--ai-violet)';
                  } else {
                    iconColor = 'var(--ai-violet)';
                  }
                }

                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleItemClick(item)}
                    title={collapsed ? item.label : undefined}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: collapsed ? 'center' : 'space-between',
                      gap: '10px',
                      padding: collapsed ? '10px' : '8px 12px',
                      borderRadius: 'var(--radius-md)',
                      background: isActive ? activeBg : 'transparent',
                      color: isActive ? activeColor : 'var(--sidebar-nav-text, var(--text-primary))',
                      fontWeight: isActive ? '700' : '600',
                      fontSize: '0.86rem',
                      border: 'none',
                      cursor: 'pointer',
                      textAlign: 'left',
                      transition: 'all 0.16s ease',
                      position: 'relative'
                    }}
                    onMouseEnter={e => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'var(--sidebar-hover-bg, var(--bg-subtle))';
                        e.currentTarget.style.color = 'var(--sidebar-active-text, var(--primary))';
                      }
                    }}
                    onMouseLeave={e => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--sidebar-nav-text, var(--text-primary))';
                      }
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <Icon size={18} color={iconColor} />
                      {!collapsed && <span>{item.label}</span>}
                    </div>

                    {!collapsed && item.isAi && (
                      <span className="badge badge-violet" style={{ fontSize: '0.6rem', padding: '1px 5px' }}>
                        AI
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Collapse / Expand Toggle Button at Bottom */}
        <div style={{ paddingTop: '12px', borderTop: '1px solid var(--border-glass)', marginTop: '12px' }}>
          <button
            type="button"
            onClick={() => setCollapsed(!collapsed)}
            className="btn-secondary"
            style={{
              width: '100%',
              padding: '6px',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              border: 'none',
              background: 'transparent'
            }}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight size={16} /> : <><ChevronLeft size={16} /> <span>Collapse</span></>}
          </button>
        </div>
      </aside>

      {/* Quick Water Modal */}
      {showWaterModal && (
        <WaterModal
          isOpen={showWaterModal}
          onClose={() => setShowWaterModal(false)}
          onWaterLogged={() => useStore.getState().refreshAllData()}
        />
      )}

      {/* Quick Activity Modal */}
      {showActivityModal && (
        <ActivityModal
          isOpen={showActivityModal}
          onClose={() => setShowActivityModal(false)}
          onActivitySaved={() => useStore.getState().refreshAllData()}
        />
      )}
    </>
  );
};
