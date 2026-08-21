import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import {
  Calendar, ChevronLeft, ChevronRight, Flame, Droplets, Utensils,
  Award, CheckCircle2, AlertCircle, Sparkles, Download, RefreshCw,
  TrendingUp, BarChart2, ShieldCheck, Wifi, WifiOff, FileText, Check, Clock
} from 'lucide-react';
import { getToday, addDays, subtractDays, formatDate, parseDateParts } from '../utils/dateUtils';

export const WeeklySummaryPage = () => {
  const { profile, targets, isOnline, triggerSync, navigate } = useStore();

  const getMondayIso = (dateStr = getToday()) => {
    const { year, month, day } = parseDateParts(dateStr);
    const d = new Date(year, month - 1, day, 12, 0, 0);
    const dayOfWeek = d.getDay();
    const diff = d.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
    const mon = new Date(year, month - 1, diff, 12, 0, 0);
    const y = mon.getFullYear();
    const m = String(mon.getMonth() + 1).padStart(2, '0');
    const dayNum = String(mon.getDate()).padStart(2, '0');
    return `${y}-${m}-${dayNum}`;
  };

  const [selectedWeekStart, setSelectedWeekStart] = useState(getMondayIso());
  const [weeklyData, setWeeklyData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const todayStr = getToday();

  useEffect(() => {
    fetchWeeklyData(selectedWeekStart);
  }, [selectedWeekStart]);

  const fetchWeeklyData = async (weekStartStr) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getWeeklySummary(weekStartStr);
      setWeeklyData(data);
    } catch (err) {
      console.warn("Failed to fetch weekly summary:", err);
      setError("Unable to load weekly summary.");
    } finally {
      setLoading(false);
    }
  };

  const handlePrevWeek = () => {
    setSelectedWeekStart(prev => subtractDays(prev, 7));
  };

  const handleNextWeek = () => {
    setSelectedWeekStart(prev => addDays(prev, 7));
  };

  const weekEndStr = addDays(selectedWeekStart, 6);
  const summary = weeklyData?.summary || weeklyData?.weekly_averages || {};
  const dailyBreakdown = weeklyData?.daily_breakdown || [];
  const elapsedDays = summary.elapsed_days || 7;
  const avgLabel = summary.avg_label || (elapsedDays < 7 && elapsedDays > 0 ? `${elapsedDays}-Day Average` : "7-Day Average");

  const formatLiters = (ml) => {
    if (!ml || isNaN(ml) || ml <= 0) return '0.0';
    const l = ml / 1000;
    if (Number.isInteger(l)) return `${l.toFixed(1)}`;
    const fixed = l.toFixed(2);
    return fixed.endsWith('0') ? l.toFixed(1) : fixed;
  };

  return (
    <div className="page-container">
      
      {/* 1. Header & Week Navigation */}
      <div className="wellness-card" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)', marginBottom: '4px' }}>
              <BarChart2 size={20} />
              <h2 style={{ fontSize: '1.5rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>Weekly Nutrition Summary</h2>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', margin: 0 }}>
              Multi-day aggregation of calorie budget adherence and macro consistency.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-subtle)', padding: '6px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-glass)' }}>
            <button
              type="button"
              onClick={handlePrevWeek}
              className="btn-secondary"
              style={{ padding: '6px 10px', fontSize: '0.8rem' }}
              title="Previous Week"
            >
              <ChevronLeft size={16} />
            </button>
            <span style={{ fontSize: '0.86rem', fontWeight: '800', color: 'var(--text-primary)', minWidth: '180px', textAlign: 'center' }}>
              {formatDate(selectedWeekStart)} – {formatDate(weekEndStr)}
            </span>
            <button
              type="button"
              onClick={handleNextWeek}
              className="btn-secondary"
              style={{ padding: '6px 10px', fontSize: '0.8rem' }}
              title="Next Week"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="wellness-card" style={{ padding: '48px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <RefreshCw size={24} className="spin" style={{ margin: '0 auto 12px auto', color: 'var(--primary)' }} />
          <div>Loading weekly summary...</div>
        </div>
      ) : error ? (
        <div className="wellness-card" style={{ padding: '36px', textAlign: 'center' }}>
          <AlertCircle size={32} color="#DC4C4C" style={{ margin: '0 auto 12px auto' }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: 'var(--text-primary)', margin: '0 0 6px 0' }}>
            {error}
          </h3>
          <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', margin: '0 0 16px 0' }}>
            Could not retrieve summary metrics for this week.
          </p>
          <button
            type="button"
            onClick={() => fetchWeeklyData(selectedWeekStart)}
            className="btn-primary"
            style={{ padding: '8px 18px', fontSize: '0.84rem' }}
          >
            Try Again
          </button>
        </div>
      ) : (
        <>
          {/* 2. Key Averages Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            <div className="wellness-card" style={{ padding: '20px' }}>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>
                {avgLabel ? `${avgLabel.toUpperCase()} INTAKE` : 'DAILY AVERAGE INTAKE'}
              </span>
              <div style={{ fontSize: '1.45rem', fontWeight: '800', color: 'var(--calorie-orange)', margin: '4px 0' }}>
                {Math.round(summary.avg_daily_calories || 0)} <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>kcal/day</span>
              </div>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Target: {Math.round(summary.calorie_target || targets?.target_calories || 2000)} kcal
              </span>
            </div>

            <div className="wellness-card" style={{ padding: '20px' }}>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>
                {avgLabel ? `${avgLabel.toUpperCase()} PROTEIN` : 'DAILY AVERAGE PROTEIN'}
              </span>
              <div style={{ fontSize: '1.45rem', fontWeight: '800', color: 'var(--macro-protein)', margin: '4px 0' }}>
                {Math.round(summary.avg_protein_g || 0)} <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>g/day</span>
              </div>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Target: {Math.round(summary.protein_target_g || targets?.protein_g || 120)} g
              </span>
            </div>

            <div className="wellness-card" style={{ padding: '20px' }}>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>
                {avgLabel ? `${avgLabel.toUpperCase()} HYDRATION` : 'AVERAGE HYDRATION'}
              </span>
              <div style={{ fontSize: '1.45rem', fontWeight: '800', color: 'var(--hydration-cyan)', margin: '4px 0' }}>
                {formatLiters(summary.avg_water_ml || 0)} <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>L/day</span>
              </div>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Target: {formatLiters(summary.water_target_ml || targets?.water_ml || 2500)} L
              </span>
            </div>

            <div className="wellness-card" style={{ padding: '20px' }}>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>
                GOAL ADHERENCE
              </span>
              <div style={{ fontSize: '1.45rem', fontWeight: '800', color: 'var(--primary)', margin: '4px 0' }}>
                {Math.round(summary.goal_adherence_pct || 0)}%
              </div>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {summary.days_with_complete_logging || 0} / {elapsedDays} days complete
              </span>
            </div>
          </div>

          {/* 3. 7-Day Day-by-Day Breakdown */}
          <div className="wellness-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                  Day-by-Day Breakdown
                </h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Detailed meal and water journal for each day of the week
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {dailyBreakdown.map((dayItem, idx) => {
                const isToday = dayItem.is_today || dayItem.date === todayStr;
                const isFuture = dayItem.is_future || dayItem.date > todayStr;
                const cal = dayItem.calories_consumed !== undefined ? dayItem.calories_consumed : (dayItem.calories || 0);
                const pro = dayItem.protein_consumed_g !== undefined ? dayItem.protein_consumed_g : (dayItem.protein_g || 0);
                const carb = dayItem.carbs_consumed_g !== undefined ? dayItem.carbs_consumed_g : (dayItem.carbs_g || 0);
                const fat = dayItem.fat_consumed_g !== undefined ? dayItem.fat_consumed_g : (dayItem.fat_g || 0);
                const waterMl = dayItem.water_consumed_ml !== undefined ? dayItem.water_consumed_ml : (dayItem.water_ml || 0);
                const hasData = dayItem.has_data || (cal > 0 || waterMl > 0 || (dayItem.meals_logged_count || 0) > 0);

                if (isFuture) {
                  return (
                    <div
                      key={idx}
                      style={{
                        padding: '14px 18px',
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--bg-subtle)',
                        border: '1px dashed var(--border-glass)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        opacity: 0.75,
                        cursor: 'default'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '0.92rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                              {dayItem.day_name || dayItem.day} ({formatDate(dayItem.date)})
                            </span>
                            <span className="badge" style={{ background: 'var(--bg-card)', color: 'var(--text-muted)', fontSize: '0.65rem', padding: '1px 6px' }}>
                              Upcoming
                            </span>
                          </div>
                          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                            No tracking data yet
                          </div>
                        </div>
                      </div>

                      <div style={{ textAlign: 'right', color: 'var(--text-muted)', fontSize: '0.84rem' }}>
                        -- kcal
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={idx}
                    onClick={() => navigate(`/meal-history?date=${dayItem.date}`)}
                    style={{
                      padding: '14px 18px',
                      borderRadius: 'var(--radius-md)',
                      background: isToday ? 'rgba(22, 124, 90, 0.04)' : 'var(--bg-subtle)',
                      border: isToday ? '1.5px solid var(--primary)' : '1px solid var(--border-glass)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      transition: 'all 0.16s ease'
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.borderColor = 'var(--primary)';
                      e.currentTarget.style.background = 'var(--primary-light)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.borderColor = isToday ? 'var(--primary)' : 'var(--border-glass)';
                      e.currentTarget.style.background = isToday ? 'rgba(22, 124, 90, 0.04)' : 'var(--bg-subtle)';
                    }}
                    title={`Click to view meal history for ${dayItem.date}`}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.92rem', fontWeight: '800', color: 'var(--text-primary)' }}>
                          {dayItem.day_name || dayItem.day} ({formatDate(dayItem.date)})
                        </span>
                        {isToday && (
                          <span className="badge badge-emerald" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
                            Today
                          </span>
                        )}
                      </div>

                      {hasData ? (
                        <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                          P: {Math.round(pro * 10) / 10}g • C: {Math.round(carb * 10) / 10}g • F: {Math.round(fat * 10) / 10}g
                        </div>
                      ) : (
                        <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          No meals logged
                        </div>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '1.05rem', fontWeight: '800', color: hasData ? 'var(--calorie-orange)' : 'var(--text-muted)' }}>
                          {Math.round(cal)} kcal
                        </div>
                        <span style={{ fontSize: '0.72rem', color: 'var(--hydration-cyan)', fontWeight: '700' }}>
                          💧 {formatLiters(waterMl)} L
                        </span>
                      </div>
                      <ChevronRight size={16} color="var(--primary)" />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

    </div>
  );
};

