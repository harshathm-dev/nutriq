import React, { useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { Bell, Clock, X, Check, FileText, Utensils, AlertCircle } from 'lucide-react';

export const ReminderToast = () => {
  const { user, navigate, setTab, pendingReminder, setPendingReminder } = useStore();
  const [activeReminder, setActiveReminder] = useState(null);
  const [loadingAction, setLoadingAction] = useState(false);

  useEffect(() => {
    if (!user) return;

    // Initial check
    checkPending();

    // Check periodically every 60 seconds
    const interval = setInterval(checkPending, 60000);

    // Also check on window focus
    const handleFocus = () => checkPending();
    window.addEventListener('focus', handleFocus);

    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', handleFocus);
    };
  }, [user]);

  const checkPending = async () => {
    try {
      const nowIso = new Date().toISOString();
      const res = await api.getPendingReminders(nowIso);
      if (res && res.has_pending) {
        setActiveReminder(res);
        setPendingReminder(res);

        // Optional Web Notification
        if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
          // Avoid spamming system notification if already shown recently
          const lastShownKey = `nutriq_notif_${res.meal_type}_${new Date().toISOString().split('T')[0]}`;
          const lastShown = sessionStorage.getItem(lastShownKey);
          if (!lastShown) {
            new Notification(res.title || 'NutriQ Reminder', {
              body: res.message || 'NutriQ notification',
              icon: '/favicon.ico'
            });
            sessionStorage.setItem(lastShownKey, 'true');
          }
        }
      } else {
        setActiveReminder(null);
        setPendingReminder(null);
      }
    } catch (e) {
      console.warn("Could not check pending reminders:", e);
    }
  };

  const handleAction = async (actionType) => {
    if (!activeReminder) return;
    setLoadingAction(true);
    const mType = activeReminder.meal_type;

    try {
      await api.respondToReminder(mType, actionType);
      
      if (actionType === 'log_meal') {
        if (mType === 'daily_summary') {
          navigate('/daily-summary');
        } else {
          navigate(`/log-meal?meal_type=${mType}`);
        }
      }
      
      setActiveReminder(null);
      setPendingReminder(null);
    } catch (e) {
      console.warn("Failed to submit reminder action:", e);
    } finally {
      setLoadingAction(false);
    }
  };

  if (!activeReminder) return null;

  const isDailySummary = activeReminder.meal_type === 'daily_summary';

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 9999,
        width: '380px',
        maxWidth: 'calc(100vw - 48px)',
        background: '#FFFFFF',
        border: '1px solid #D8E2DC',
        boxShadow: '0 12px 36px rgba(23, 34, 29, 0.14)',
        borderRadius: 'var(--radius-lg)',
        padding: '18px 20px',
        color: '#17221D',
        animation: 'slideUp 0.3s ease-out'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: isDailySummary ? 'linear-gradient(135deg, #7357D9 0%, #5B21B6 100%)' : 'linear-gradient(135deg, #167C5A 0%, #0F684B 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            {isDailySummary ? <FileText size={18} color="#fff" /> : <Bell size={18} color="#fff" />}
          </div>
          <div>
            <div style={{ fontSize: '0.95rem', fontWeight: '800', color: '#17221D' }}>
              {activeReminder.title}
            </div>
            <div style={{ fontSize: '0.72rem', color: '#7A8981', fontWeight: '500' }}>
              NutriQ Smart Notifications
            </div>
          </div>
        </div>

        <button
          onClick={() => handleAction('dismiss')}
          disabled={loadingAction}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '4px'
          }}
          title="Dismiss reminder"
        >
          <X size={16} />
        </button>
      </div>

      <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.45, marginBottom: '14px' }}>
        {activeReminder.message}
      </p>

      {/* Action Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={() => handleAction('log_meal')}
          disabled={loadingAction}
          className="btn-primary"
          style={{ flex: '1 1 auto', padding: '8px 12px', fontSize: '0.82rem', justifyContent: 'center' }}
        >
          {isDailySummary ? 'View Summary' : 'Log Meal'}
        </button>

        {!isDailySummary && (
          <button
            onClick={() => handleAction('remind_later')}
            disabled={loadingAction}
            className="btn-secondary"
            style={{ flex: '1 1 auto', padding: '8px 10px', fontSize: '0.8rem', justifyContent: 'center' }}
          >
            <Clock size={13} /> Remind Later
          </button>
        )}

        <button
          onClick={() => handleAction('dismiss')}
          disabled={loadingAction}
          className="btn-secondary"
          style={{ padding: '8px 12px', fontSize: '0.8rem', color: 'var(--text-muted)' }}
          title="Dismiss for today"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
};

export default ReminderToast;
