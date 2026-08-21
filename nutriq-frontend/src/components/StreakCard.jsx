import React, { useState, useEffect } from 'react';
import { Flame, Trophy, Calendar, Sparkles, Check, ChevronRight, Award, X, CheckCircle2, Zap } from 'lucide-react';
import { api } from '../services/api';
import { getToday } from '../utils/dateUtils';

const MILESTONES = [
  { days: 3, title: "3-Day Consistency", desc: "Logged nutrition for 3 consecutive days." },
  { days: 7, title: "7-Day Perfect Week", desc: "A full week of consistent nutrition tracking." },
  { days: 14, title: "14-Day Momentum", desc: "Two weeks strong. Habits becoming second nature." },
  { days: 30, title: "30-Day Legend", desc: "A full month of wellness dedication." }
];

export const StreakCard = ({ onLogClick, onClose }) => {
  const [streakData, setStreakData] = useState({
    current_streak: 0,
    longest_streak: 0,
    total_active_days: 0,
    completed_today: false,
    weekly_history: []
  });
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchStreak = async () => {
    try {
      const data = await api.getStreakStatus();
      if (data) {
        setStreakData(data);
      }
    } catch (e) {
      console.warn("Failed to load streak data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStreak();
  }, []);

  const currentStreak = Number(streakData.current_streak || 0);
  const isCompletedToday = Boolean(streakData.completed_today);
  const longestStreak = Number(streakData.longest_streak || 0);
  const totalDays = Number(streakData.total_active_days || 0);
  const weekly = Array.isArray(streakData.weekly_history) ? streakData.weekly_history : [];

  const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  return (
    <>
      {/* Compact Clean Dashboard Card */}
      <div
        className="wellness-card wellness-card-interactive"
        onClick={() => setShowModal(true)}
        style={{
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          gap: '16px',
          height: '100%',
          cursor: 'pointer'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: isCompletedToday ? 'var(--accent-gradient)' : 'var(--streak-badge-bg, #FFF3EB)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Flame size={22} color={isCompletedToday ? "#FFFFFF" : "var(--streak, #E76F51)"} fill={isCompletedToday ? "#FFFFFF" : "var(--streak, #F4A261)"} />
            </div>
            <div>
              <span style={{ fontSize: '0.74rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Habit Streak
              </span>
              <h4 style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--text-primary)', margin: 0 }}>
                {currentStreak} Day Streak
              </h4>
            </div>
          </div>
          <span className={`badge ${isCompletedToday ? 'badge-emerald' : 'badge-amber'}`}>
            {isCompletedToday ? '✓ Logged Today' : 'Pending Today'}
          </span>
        </div>

        {/* 7-Day Activity Indicator (Monday to Sunday) */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-subtle)', padding: '10px 14px', borderRadius: 'var(--radius-md)' }}>
          {daysOfWeek.map((dayName, idx) => {
            const histItem = weekly.find(item => item.day_name === dayName) || weekly[idx] || {};
            const done = Boolean(histItem.completed || histItem.logged);
            return (
              <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <span style={{ fontSize: '0.68rem', fontWeight: '600', color: 'var(--text-secondary)' }}>
                  {dayName}
                </span>
                <div style={{
                  width: '22px',
                  height: '22px',
                  borderRadius: '50%',
                  background: done ? 'var(--streak-completed, var(--primary))' : 'transparent',
                  border: done ? 'none' : '1.5px solid var(--streak-inactive, var(--border-glass))',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#FFFFFF',
                  fontSize: '0.65rem'
                }}>
                  {done ? <Check size={13} strokeWidth={3} /> : <span style={{ color: 'var(--text-muted)' }}>○</span>}
                </div>
              </div>
            );
          })}
        </div>

        {/* Motivational Tip */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem' }}>
          <span style={{ color: 'var(--text-secondary)' }}>
            {isCompletedToday ? "You're building a consistent nutrition habit." : "Log a meal today to continue your streak."}
          </span>
          <span style={{ color: 'var(--primary)', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '2px' }}>
            Details <ChevronRight size={14} />
          </span>
        </div>
      </div>

      {/* Streak Details Modal */}
      {(showModal || onClose) && (
        <div className="modal-overlay" onClick={() => { setShowModal(false); if (onClose) onClose(); }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px', padding: '28px' }}>
            
            {/* Modal Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '12px',
                  background: 'var(--accent-gradient)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Flame size={26} color="#FFFFFF" fill="#FFFFFF" />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.3rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                    Streak & Habit Consistency
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {isCompletedToday ? "You're building a consistent nutrition habit." : "Log a meal today to continue your streak."}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => { setShowModal(false); if (onClose) onClose(); }}
                className="btn-secondary"
                style={{ padding: '6px', borderRadius: '50%', border: 'none', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Streak Metrics Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '24px' }}>
              <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: '600' }}>Current Streak</span>
                <h4 style={{ fontSize: '1.5rem', fontWeight: '800', color: '#E76F51', margin: '4px 0 0 0' }}>
                  {currentStreak} <span style={{ fontSize: '0.85rem' }}>days</span>
                </h4>
              </div>

              <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: '600' }}>Longest Streak</span>
                <h4 style={{ fontSize: '1.5rem', fontWeight: '800', color: 'var(--primary)', margin: '4px 0 0 0' }}>
                  {longestStreak} <span style={{ fontSize: '0.85rem' }}>days</span>
                </h4>
              </div>

              <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: '600' }}>Total Active</span>
                <h4 style={{ fontSize: '1.5rem', fontWeight: '800', color: 'var(--text-primary)', margin: '4px 0 0 0' }}>
                  {totalDays} <span style={{ fontSize: '0.85rem' }}>days</span>
                </h4>
              </div>
            </div>

            {/* Weekly Activity Tracker */}
            <div style={{ marginBottom: '24px' }}>
              <h5 style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '10px' }}>
                This Week's Activity
              </h5>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '8px', background: 'var(--bg-subtle)', padding: '16px 12px', borderRadius: 'var(--radius-md)' }}>
                {daysOfWeek.map((d, idx) => {
                  const hist = weekly.find(item => item.day_name === d) || weekly[idx] || {};
                  const done = Boolean(hist.completed || hist.logged);
                  return (
                    <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '0.72rem', fontWeight: '600', color: 'var(--text-secondary)' }}>{d}</span>
                      <div style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        background: done ? 'var(--streak-completed, var(--primary))' : 'var(--bg-elevated, #FFFFFF)',
                        border: done ? 'none' : '1.5px solid var(--streak-inactive, var(--border-glass))',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: done ? '#FFFFFF' : 'var(--text-muted)',
                        fontSize: '0.75rem',
                        fontWeight: '700'
                      }}>
                        {done ? <Check size={16} strokeWidth={3} /> : '○'}
                      </div>
                      <span style={{ fontSize: '0.62rem', color: done ? 'var(--streak-completed, var(--primary))' : 'var(--text-muted)', fontWeight: '600' }}>
                        {done ? 'Completed' : 'Pending'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Milestone Cards */}
            <div>
              <h5 style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '10px' }}>
                Consistency Milestones
              </h5>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {MILESTONES.map((m, idx) => {
                  const achieved = currentStreak >= m.days || longestStreak >= m.days;
                  return (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '10px 14px',
                        borderRadius: 'var(--radius-md)',
                        background: achieved ? 'var(--primary-light)' : 'var(--bg-subtle)',
                        border: achieved ? '1px solid rgba(31, 122, 90, 0.25)' : '1px solid var(--border-glass)'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Trophy size={18} color={achieved ? "var(--primary)" : "var(--text-muted)"} />
                        <div>
                          <span style={{ fontSize: '0.84rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                            {m.title}
                          </span>
                          <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                            {m.desc}
                          </p>
                        </div>
                      </div>
                      <span style={{ fontSize: '0.74rem', fontWeight: '700', color: achieved ? 'var(--primary)' : 'var(--text-muted)' }}>
                        {achieved ? '✓ Unlocked' : `${m.days} Days`}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default StreakCard;
