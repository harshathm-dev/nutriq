import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { StreakCard } from './StreakCard';
import { WaterModal } from './WaterModal';
import {
  Flame, Wifi, WifiOff, RefreshCw, Sun, Moon,
  Droplets, User, Sparkles, Settings, LogOut, ChevronDown, CheckCircle2
} from 'lucide-react';

export const Navbar = () => {
  const {
    isOnline, triggerSync, user, profile,
    targets, dailyAnalytics,
    theme, setTheme, logout, navigate, activeTab, refreshAllData
  } = useStore();

  const [streakData, setStreakData] = useState(null);
  const [showStreakModal, setShowStreakModal] = useState(false);
  const [showWaterModal, setShowWaterModal] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

  const displayName = profile?.name?.trim() || user?.email?.split('@')[0] || 'User';

  useEffect(() => {
    fetchQuickData();
  }, [activeTab]);

  const fetchQuickData = async () => {
    try {
      const stk = await api.getStreak().catch(() => null);
      if (stk) setStreakData(stk);
      await refreshAllData();
    } catch (e) {}
  };

  const streakDays = streakData?.current_streak || 1;

  // Single Source of Truth for Water intake and target
  const consumedWaterMl = dailyAnalytics?.consumed?.water_ml !== undefined
    ? Number(dailyAnalytics.consumed.water_ml)
    : 0;

  const targetWaterMl = targets?.water_ml !== undefined && targets?.water_ml > 0
    ? Number(targets.water_ml)
    : 2500;

  const formatLiters = (ml) => {
    if (!ml || isNaN(ml) || ml <= 0) return '0.0';
    const l = ml / 1000;
    if (Number.isInteger(l)) return `${l.toFixed(1)}`;
    const fixed = l.toFixed(2);
    return fixed.endsWith('0') ? l.toFixed(1) : fixed;
  };

  const waterLiters = formatLiters(consumedWaterMl);
  const targetLiters = formatLiters(targetWaterMl);

  const rawWaterPct = targetWaterMl > 0 ? (consumedWaterMl / targetWaterMl) * 100 : 0;
  const waterPct = Math.min(100, Math.round(rawWaterPct));
  const isTargetAchieved = consumedWaterMl >= targetWaterMl && targetWaterMl > 0;

  return (
    <>
      <header
        className="wellness-card"
        style={{
          margin: '16px 24px 0 24px',
          padding: '12px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          zIndex: 40,
          position: 'sticky',
          top: '16px'
        }}
      >
        {/* Left: Brand & Logo */}
        <div
          style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', flexShrink: 0 }}
          onClick={() => navigate('/dashboard')}
        >
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            background: 'var(--primary-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(31, 122, 90, 0.25)'
          }}>
            <Flame size={24} color="#FFFFFF" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <h1 style={{ fontSize: '1.28rem', fontWeight: '800', color: 'var(--primary)', margin: 0, lineHeight: 1.1 }}>
                NutriQ
              </h1>
              <span className="badge badge-emerald" style={{ fontSize: '0.62rem', padding: '1px 6px' }}>
                WELLNESS
              </span>
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: '500' }}>
              Personal Nutrition Intelligence
            </span>
          </div>
        </div>
        {/* Right Actions: Streak, Water, Sync, Theme, Profile */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          
          {/* Streak Badge Button */}
          <button
            type="button"
            onClick={() => setShowStreakModal(true)}
            style={{
              height: '36px',
              padding: '6px 13px',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              border: '1px solid var(--border-glass)',
              background: 'var(--streak-badge-bg, #FFF9F5)',
              color: 'var(--streak, #D97706)',
              fontWeight: '700',
              fontSize: '0.82rem',
              boxShadow: 'none',
              transition: 'all 0.2s ease'
            }}
            title="Click to view streak breakdown"
          >
            <Flame size={15} color="var(--streak, #E76F51)" fill="var(--streak, #F4A261)" />
            <span>{streakDays} Day Streak</span>
          </button>

          {/* Water Widget Button */}
          <button
            type="button"
            onClick={() => setShowWaterModal(true)}
            style={{
              height: '36px',
              padding: '6px 13px',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              border: '1px solid var(--border-glass)',
              background: isTargetAchieved ? 'var(--success-bg, #E1F4EA)' : 'var(--water-badge, #DDF5F4)',
              color: isTargetAchieved ? 'var(--success, #16865F)' : 'var(--water-text, #159A9C)',
              fontWeight: '700',
              fontSize: '0.82rem',
              boxShadow: 'none',
              transition: 'all 0.2s ease'
            }}
            title={`Daily Hydration: ${waterLiters} / ${targetLiters} L (${waterPct}%) - Click to log water`}
          >
            <Droplets
              size={15}
              color={isTargetAchieved ? "var(--success, #16865F)" : "var(--water, #159A9C)"}
              fill={isTargetAchieved ? "var(--success, #16865F)" : "var(--water, #159A9C)"}
            />
            <span>
              {waterLiters} / {targetLiters} L{isTargetAchieved ? ' ✓' : ''}
            </span>
          </button>

          {/* Wi-Fi / Online Connectivity Indicator */}
          <div
            onClick={triggerSync}
            style={{
              height: '36px',
              padding: '6px 13px',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              border: '1px solid var(--border-glass)',
              background: isOnline ? 'var(--success-bg, #E1F4EA)' : 'var(--error-bg, #FDE8E8)',
              color: isOnline ? 'var(--success, #16865F)' : 'var(--error, #DC4C4C)',
              fontWeight: '700',
              fontSize: '0.82rem',
              boxShadow: 'none',
              transition: 'all 0.2s ease'
            }}
            title={isOnline ? "Connected to NutriQ Cloud (Online)" : "Offline Mode - All features available locally"}
          >
            {isOnline ? (
              <>
                <Wifi size={14} color="var(--success, #16865F)" />
                <span>Online</span>
              </>
            ) : (
              <>
                <WifiOff size={14} color="var(--error, #DC4C4C)" />
                <span>Offline</span>
              </>
            )}
          </div>

          {/* Theme Toggle */}
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="btn-secondary"
            style={{ padding: '8px', borderRadius: '50%', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            title="Toggle Light / Dark Wellness Mode"
          >
            {theme === 'dark' ? <Sun size={16} color="#F4A261" /> : <Moon size={16} color="#66736B" />}
          </button>

          {/* User Profile Avatar & Dropdown */}
          {user ? (
            <div style={{ position: 'relative' }}>
              <div
                onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  cursor: 'pointer',
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-full)',
                  border: '1px solid var(--border-glass)',
                  background: 'var(--bg-subtle)'
                }}
              >
                <div style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  background: 'var(--primary-gradient)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.78rem',
                  fontWeight: '800',
                  color: '#FFFFFF'
                }}>
                  {displayName.charAt(0).toUpperCase()}
                </div>
                <span style={{ fontSize: '0.84rem', fontWeight: '700', color: 'var(--text-primary)', maxWidth: '100px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {displayName}
                </span>
                <ChevronDown size={14} color="var(--text-muted)" />
              </div>

              {userDropdownOpen && (
                <div
                  className="wellness-card"
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: '42px',
                    width: '180px',
                    padding: '8px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    zIndex: 60,
                    boxShadow: 'var(--shadow-lg)'
                  }}
                >
                  <button
                    type="button"
                    onClick={() => { setUserDropdownOpen(false); navigate('/settings'); }}
                    className="btn-secondary"
                    style={{ justifyContent: 'flex-start', border: 'none', padding: '8px 10px', fontSize: '0.82rem', width: '100%' }}
                  >
                    <Settings size={15} /> Settings
                  </button>
                  <button
                    type="button"
                    onClick={() => { setUserDropdownOpen(false); navigate('/privacy'); }}
                    className="btn-secondary"
                    style={{ justifyContent: 'flex-start', border: 'none', padding: '8px 10px', fontSize: '0.82rem', width: '100%' }}
                  >
                    <User size={15} /> Privacy & Data
                  </button>
                  <div style={{ height: '1px', background: 'var(--border-glass)', margin: '4px 0' }} />
                  <button
                    type="button"
                    onClick={() => { setUserDropdownOpen(false); logout(); }}
                    className="btn-secondary"
                    style={{ justifyContent: 'flex-start', border: 'none', padding: '8px 10px', fontSize: '0.82rem', width: '100%', color: 'var(--error-rose)' }}
                  >
                    <LogOut size={15} /> Logout
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={() => navigate('/login')}
              className="btn-primary"
              style={{ padding: '8px 16px', fontSize: '0.84rem' }}
            >
              Sign In
            </button>
          )}
        </div>
      </header>

      {/* Embedded Streak Modal */}
      {showStreakModal && (
        <div className="modal-overlay" onClick={() => setShowStreakModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px', padding: '24px' }}>
            <StreakCard onClose={() => setShowStreakModal(false)} />
          </div>
        </div>
      )}

      {/* Embedded Water Modal */}
      {showWaterModal && (
        <WaterModal
          isOpen={showWaterModal}
          onClose={() => {
            setShowWaterModal(false);
            fetchQuickData();
          }}
          onWaterLogged={() => fetchQuickData()}
        />
      )}
    </>
  );
};
