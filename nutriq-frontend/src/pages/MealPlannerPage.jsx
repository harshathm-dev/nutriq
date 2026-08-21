import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useStore } from '../store/useStore';
import {
  CalendarDays, Sparkles, RefreshCw, CheckCircle2, Flame,
  AlertCircle, ChevronRight, Clock, Utensils, RotateCcw, Plus
} from 'lucide-react';

export const MealPlannerPage = () => {
  const [days, setDays] = useState(7);
  const [budget, setBudget] = useState('medium');
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [noticeMessage, setNoticeMessage] = useState('');
  const [activeDay, setActiveDay] = useState('Monday');
  const [planRecordId, setPlanRecordId] = useState(null);

  const { user, profile, targets, navigate } = useStore();

  const daysList = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  useEffect(() => {
    loadActivePlan();
  }, [user]);

  const loadActivePlan = async () => {
    if (!user) return;
    try {
      const res = await api.getActiveMealPlan();
      if (res && res.plan_payload) {
        setPlanRecordId(res.id || null);
        const parsed = typeof res.plan_payload === 'string' ? JSON.parse(res.plan_payload) : res.plan_payload;
        if (parsed && parsed.days) {
          setPlan(parsed);
          const keys = Object.keys(parsed.days);
          if (keys.length > 0) setActiveDay(keys[0]);
        }
      }
    } catch (e) {
      console.warn("No active meal plan loaded:", e);
    }
  };

  const handleGenerate = async () => {
    if (loading) return;
    setLoading(true);
    setErrorMessage('');
    setNoticeMessage('');

    try {
      const res = await api.generateMealPlan(days, budget);
      if (res && res.id) setPlanRecordId(res.id);
      const parsed = typeof res.plan_payload === 'string' ? JSON.parse(res.plan_payload) : res.plan_payload;
      if (parsed) {
        setPlan(parsed);
        const keys = Object.keys(parsed.days || {});
        if (keys.length > 0) setActiveDay(keys[0]);
        setNoticeMessage("Your meal plan has been optimized by NutriQ AI!");
      }
    } catch (err) {
      setErrorMessage(err.message || "Failed to generate meal plan. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const currentDayPlan = plan?.days ? (plan.days[activeDay] || plan.days[`Day ${daysList.indexOf(activeDay) + 1}`] || {}) : {};

  return (
    <div className="page-container">
      
      {/* 1. Header Panel */}
      <div className="wellness-card" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)', marginBottom: '4px' }}>
              <CalendarDays size={20} />
              <h2 style={{ fontSize: '1.5rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>Weekly Meal Planner</h2>
            </div>
            <span style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
              Intelligent nutrition schedules tailored to your daily targets and regional dietary preferences.
            </span>
          </div>

          <button
            type="button"
            onClick={handleGenerate}
            disabled={loading}
            className="btn-primary"
            style={{ padding: '10px 20px', fontSize: '0.88rem', gap: '8px' }}
          >
            <Sparkles size={16} />
            <span>{loading ? 'Optimizing Plan...' : 'Optimize My Plan'}</span>
          </button>
        </div>

        {noticeMessage && (
          <div style={{ marginTop: '16px', padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'var(--primary-light)', color: 'var(--primary-dark)', fontSize: '0.82rem', fontWeight: '700' }}>
            ✓ {noticeMessage}
          </div>
        )}
        {errorMessage && (
          <div style={{ marginTop: '16px', padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'var(--error-bg)', color: 'var(--error-rose)', fontSize: '0.82rem', fontWeight: '700' }}>
            ✕ {errorMessage}
          </div>
        )}
      </div>

      {/* 2. 7-Day Day Selector Bar */}
      <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
        {daysList.map((dayName) => {
          const isSelected = activeDay === dayName;
          return (
            <button
              key={dayName}
              type="button"
              onClick={() => setActiveDay(dayName)}
              style={{
                flex: 1,
                minWidth: '110px',
                padding: '12px 14px',
                borderRadius: 'var(--radius-md)',
                background: isSelected ? 'var(--primary-light)' : 'var(--bg-card, #FFFFFF)',
                border: isSelected ? '1.5px solid var(--primary)' : '1px solid var(--border-glass)',
                color: isSelected ? 'var(--primary)' : 'var(--text-primary)',
                fontWeight: isSelected ? '800' : '600',
                fontSize: '0.86rem',
                cursor: 'pointer',
                textAlign: 'center',
                boxShadow: isSelected ? 'var(--shadow-sm)' : 'none',
                transition: 'all 0.16s ease'
              }}
              onMouseEnter={(e) => {
                if (!isSelected) e.currentTarget.style.background = 'var(--bg-subtle)';
              }}
              onMouseLeave={(e) => {
                if (!isSelected) e.currentTarget.style.background = 'var(--bg-card, #FFFFFF)';
              }}
            >
              <div style={{ fontWeight: '800' }}>{dayName}</div>
              <div style={{ fontSize: '0.74rem', color: isSelected ? 'var(--primary)' : 'var(--text-secondary)', marginTop: '3px', fontWeight: '600' }}>
                4 Meal Slots
              </div>
            </button>
          );
        })}
      </div>

      {/* 3. Meal Slots Timeline for Active Day */}
      <div className="wellness-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
              Meal Plan for {activeDay}
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Target: ~{targets?.target_calories || 2000} kcal • {targets?.protein_g || 120}g Protein
            </span>
          </div>

          <button
            type="button"
            onClick={() => navigate('/log-meal')}
            className="btn-secondary"
            style={{ padding: '6px 14px', fontSize: '0.82rem' }}
          >
            <Plus size={15} /> Log to Journal
          </button>
        </div>

        {/* 4 Meal Slots: Breakfast, Lunch, Evening Snack, Dinner */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
          {[
            { slotKey: 'breakfast', label: 'Breakfast', time: '08:00', icon: '🌅' },
            { slotKey: 'lunch', label: 'Lunch', time: '13:00', icon: '☀️' },
            { slotKey: 'snack', label: 'Evening Snack', time: '17:00', icon: '☕' },
            { slotKey: 'dinner', label: 'Dinner', time: '20:00', icon: '🌙' }
          ].map(({ slotKey, label, time, icon }) => {
            const slotData = currentDayPlan[slotKey] || {};
            const foodName = slotData.food_name || slotData.name || (slotKey === 'breakfast' ? 'Idli with Sambar & Chutney' : slotKey === 'lunch' ? 'Brown Rice with Dal & Paneer Curry' : slotKey === 'snack' ? 'Sprouted Moong Salad & Green Tea' : 'Multigrain Chapati with Vegetable Korma');
            const calories = Math.round(slotData.calories || (slotKey === 'breakfast' ? 450 : slotKey === 'lunch' ? 680 : slotKey === 'snack' ? 220 : 550));
            const protein = Math.round(slotData.protein_g || slotData.protein || (slotKey === 'breakfast' ? 16 : slotKey === 'lunch' ? 32 : slotKey === 'snack' ? 12 : 24));
            const carbs = Math.round(slotData.carbs_g || slotData.carbs || (slotKey === 'breakfast' ? 65 : slotKey === 'lunch' ? 95 : slotKey === 'snack' ? 28 : 70));

            return (
              <div
                key={slotKey}
                style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border-glass)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '12px'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.74rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <span>{icon}</span> {label} • {time}
                    </span>
                    <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>
                      Optimized
                    </span>
                  </div>

                  <h4 style={{ fontSize: '0.96rem', fontWeight: '800', color: 'var(--text-primary)', margin: 0 }}>
                    {foodName}
                  </h4>
                </div>

                <div style={{ paddingTop: '8px', borderTop: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.94rem', fontWeight: '800', color: 'var(--calorie-orange)' }}>
                    {calories} kcal
                  </span>
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                    P: {protein}g • C: {carbs}g
                  </span>
                </div>
              </div>
            );
          })}
        </div>

      </div>

    </div>
  );
};
