import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../services/api';
import { useStore } from '../store/useStore';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine
} from 'recharts';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Sparkles,
  Award,
  CheckCircle2,
  AlertCircle,
  PlusCircle,
  Droplet,
  Flame,
  Utensils,
  Calendar,
  ChevronRight,
  Activity,
  Scale,
  RefreshCw,
  Info,
  Layers,
  PieChart as PieIcon
} from 'lucide-react';
import { formatDate } from '../utils/dateUtils';

export const AnalyticsPage = () => {
  const [rangeKey, setRangeKey] = useState('7d'); // '7d' | '30d' | '90d' | 'custom'
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [macroViewMode, setMacroViewMode] = useState('daily'); // 'daily' | 'average'
  const { setTab } = useStore();

  useEffect(() => {
    loadAnalytics();
  }, [rangeKey, customStart, customEnd]);

  const loadAnalytics = async () => {
    if (rangeKey === 'custom' && (!customStart || !customEnd)) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAnalytics(
        rangeKey,
        rangeKey === 'custom' ? customStart : null,
        rangeKey === 'custom' ? customEnd : null
      );
      setAnalyticsData(data);
    } catch (err) {
      console.error("Failed to load analytics:", err);
      setError("Unable to load nutrition analytics. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  const summary = analyticsData?.summary || {};
  const caloriesSeries = analyticsData?.calories || [];
  const hydrationSeries = analyticsData?.hydration || [];
  const macrosSeries = analyticsData?.macros || [];
  const proteinSeries = analyticsData?.protein || [];
  const activitySeries = analyticsData?.activity || [];
  const balanceSeries = analyticsData?.calorie_balance || [];
  const weightProgress = analyticsData?.weight_progress || { history: [] };
  const insights = analyticsData?.nutrition_insights || [];
  const macroAverages = analyticsData?.macro_averages || {};
  const hydrationSummary = analyticsData?.hydration_summary || {};
  const proteinSummary = analyticsData?.protein_summary || {};
  const activitySummary = analyticsData?.activity_summary || {};

  const hasData = summary.has_data ?? (
    caloriesSeries.some(c => c.consumed > 0) ||
    hydrationSeries.some(h => h.consumed_liters > 0) ||
    activitySeries.some(a => a.calories_burned > 0) ||
    weightProgress.history.length > 0
  );

  // Custom Chart Tooltip
  const CustomChartTooltip = ({ active, payload, label, unit = '', target = null }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: '#FFFFFF',
          padding: '10px 14px',
          borderRadius: '10px',
          border: '1px solid var(--border-glass)',
          boxShadow: '0 6px 16px rgba(0,0,0,0.08)',
          fontSize: '0.82rem'
        }}>
          <div style={{ fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>
            {label}
          </div>
          {payload.map((entry, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', color: entry.color || 'var(--text-secondary)' }}>
              <span>{entry.name}:</span>
              <span style={{ fontWeight: '700' }}>
                {entry.value} {unit}
              </span>
            </div>
          ))}
          {target !== null && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', color: 'var(--text-muted)', marginTop: '4px', borderTop: '1px dashed var(--border-glass)', paddingTop: '4px' }}>
              <span>Target:</span>
              <span style={{ fontWeight: '700' }}>{target} {unit}</span>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  // Pie chart data for Macro Averages
  const macroPieData = useMemo(() => {
    const pGrams = macroAverages.avg_protein_g || 0;
    const cGrams = macroAverages.avg_carbs_g || 0;
    const fGrams = macroAverages.avg_fat_g || 0;
    const pCal = pGrams * 4;
    const cCal = cGrams * 4;
    const fCal = fGrams * 9;
    const totCal = pCal + cCal + fCal;
    if (totCal === 0) return [];
    return [
      { name: 'Protein', grams: pGrams, value: Math.round((pCal / totCal) * 100), color: '#60A5FA' },
      { name: 'Carbohydrates', grams: cGrams, value: Math.round((cCal / totCal) * 100), color: '#FBBF24' },
      { name: 'Fat', grams: fGrams, value: Math.round((fCal / totCal) * 100), color: '#F472B6' }
    ];
  }, [macroAverages]);

  return (
    <div className="page-container">
      
      {/* 1. Header & Range Navigation */}
      <div className="wellness-card" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)', marginBottom: '4px' }}>
              <BarChart3 size={22} />
              <h2 style={{ fontSize: '1.5rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                Nutrition & Progress Intelligence
              </h2>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', margin: 0 }}>
              Grounded dietary analytics, calorie adherence, hydration tracking, and body trends.
            </p>
          </div>

          {/* Time Range Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-subtle)', padding: '4px', borderRadius: 'var(--radius-md)' }}>
              {[
                { key: '7d', label: '7 Days' },
                { key: '30d', label: '30 Days' },
                { key: '90d', label: '90 Days' },
                { key: 'custom', label: 'Custom' }
              ].map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setRangeKey(tab.key)}
                  style={{
                    padding: '7px 15px',
                    borderRadius: 'var(--radius-sm)',
                    border: 'none',
                    background: rangeKey === tab.key ? 'var(--bg-active-tab, #FFFFFF)' : 'transparent',
                    color: rangeKey === tab.key ? 'var(--primary)' : 'var(--text-secondary)',
                    fontWeight: rangeKey === tab.key ? '800' : '600',
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    boxShadow: rangeKey === tab.key ? 'var(--shadow-sm)' : 'none',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={loadAnalytics}
              className="btn-secondary"
              style={{ padding: '7px 12px', fontSize: '0.8rem', height: '36px' }}
              title="Refresh Analytics"
            >
              <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Custom Date Range Selector (Shown only when 'custom' is active) */}
        {rangeKey === 'custom' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-glass)', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: '600' }}>From:</span>
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="input-field"
                style={{ height: '34px', fontSize: '0.8rem', padding: '4px 8px' }}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: '600' }}>To:</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="input-field"
                style={{ height: '34px', fontSize: '0.8rem', padding: '4px 8px' }}
              />
            </div>
            <button
              type="button"
              onClick={loadAnalytics}
              className="btn-primary"
              style={{ height: '34px', padding: '0 14px', fontSize: '0.8rem' }}
            >
              Apply Range
            </button>
          </div>
        )}
      </div>

      {/* Loading Skeleton */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="wellness-card" style={{ padding: '20px', height: '110px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                <div style={{ height: '12px', width: '40%', background: 'var(--bg-subtle)', borderRadius: '4px', marginBottom: '10px' }} />
                <div style={{ height: '24px', width: '70%', background: 'var(--bg-subtle)', borderRadius: '6px' }} />
              </div>
            ))}
          </div>
          <div className="wellness-card" style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <RefreshCw size={28} className="animate-spin" style={{ margin: '0 auto 12px auto', color: 'var(--primary)' }} />
            <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: '700', color: 'var(--text-primary)' }}>Loading your nutrition intelligence...</h4>
          </div>
        </div>
      ) : error ? (
        /* Error State */
        <div className="wellness-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
          <AlertCircle size={36} color="var(--error-rose)" style={{ margin: '0 auto 12px auto' }} />
          <h3 style={{ fontSize: '1.15rem', fontWeight: '800', color: 'var(--text-primary)', marginBottom: '8px' }}>
            Unable to load analytics
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', maxWidth: '440px', margin: '0 auto 18px auto' }}>
            {error}
          </p>
          <button type="button" onClick={loadAnalytics} className="btn-primary" style={{ padding: '8px 20px', fontSize: '0.85rem' }}>
            <RefreshCw size={15} /> Try Again
          </button>
        </div>
      ) : !hasData ? (
        /* Empty State */
        <div className="wellness-card" style={{ padding: '60px 24px', textAlign: 'center' }}>
          <div style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            background: 'var(--primary-light)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px auto',
            color: 'var(--primary)'
          }}>
            <Utensils size={28} />
          </div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '800', marginBottom: '8px', color: 'var(--text-primary)' }}>
            Not enough data yet for this period
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: '480px', margin: '0 auto 24px auto', lineHeight: '1.5' }}>
            Continue logging your daily meals, water intake, and exercises. NutriQ will automatically analyze your nutrition adherence, macronutrient distribution, and health trends here.
          </p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => setTab('add_food')}
              className="btn-primary"
              style={{ padding: '10px 22px', fontSize: '0.88rem' }}
            >
              <PlusCircle size={16} /> Log Meal
            </button>
            <button
              type="button"
              onClick={() => setTab('meal_history')}
              className="btn-secondary"
              style={{ padding: '10px 20px', fontSize: '0.88rem' }}
            >
              <Calendar size={16} /> View Journal
            </button>
          </div>
        </div>
      ) : (
        /* Full Nutrition Intelligence Visualizations */
        <>
          {/* 2. Top Summary Metric Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
            
            {/* Card 1: Avg Daily Intake */}
            <div className="wellness-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Average Daily Intake
                </span>
                <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: '#FFF3EB', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--calorie-orange)' }}>
                  <Flame size={15} />
                </div>
              </div>
              <div style={{ fontSize: '1.6rem', fontWeight: '800', color: 'var(--calorie-orange)', lineHeight: 1.2 }}>
                {Math.round(summary.avg_calories || 0)} <span style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', fontWeight: '600' }}>kcal/day</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                <span>Target: {Math.round(summary.target_calories || 2000)} kcal</span>
                {summary.calorie_change_pct !== null && summary.calorie_change_pct !== undefined && (
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '2px',
                    fontWeight: '700',
                    color: summary.calorie_change_pct > 0 ? 'var(--calorie-orange)' : 'var(--primary)'
                  }}>
                    {summary.calorie_change_pct > 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                    {Math.abs(summary.calorie_change_pct)}% vs prev
                  </span>
                )}
              </div>
            </div>

            {/* Card 2: Avg Daily Protein */}
            <div className="wellness-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Average Daily Protein
                </span>
                <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: '#EFF6FF', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#3B73E8' }}>
                  <Award size={15} />
                </div>
              </div>
              <div style={{ fontSize: '1.6rem', fontWeight: '800', color: '#3B73E8', lineHeight: 1.2 }}>
                {Math.round(summary.avg_protein || 0)} <span style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', fontWeight: '600' }}>g/day</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                <span>Target: {Math.round(summary.target_protein || 110)}g</span>
                <span style={{ fontWeight: '700', color: (summary.avg_protein || 0) >= (summary.target_protein || 110) * 0.9 ? 'var(--primary)' : '#D97706' }}>
                  {proteinSummary.achievement_pct || Math.round(((summary.avg_protein || 0) / Math.max(1, summary.target_protein || 110)) * 100)}% of goal
                </span>
              </div>
            </div>

            {/* Card 3: Avg Daily Hydration */}
            <div className="wellness-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Average Daily Hydration
                </span>
                <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: '#DDF5F4', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#159A9C' }}>
                  <Droplet size={15} />
                </div>
              </div>
              <div style={{ fontSize: '1.6rem', fontWeight: '800', color: '#159A9C', lineHeight: 1.2 }}>
                {Number(summary.avg_water_liters || 0).toFixed(1)} <span style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', fontWeight: '600' }}>L/day</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                <span>Target: {Number(summary.target_water_liters || 2.5).toFixed(1)}L</span>
                <span style={{ fontWeight: '700', color: 'var(--primary)' }}>
                  {hydrationSummary.days_goal_achieved || 0}/{hydrationSummary.total_days || summary.total_period_days || 7} days met
                </span>
              </div>
            </div>

            {/* Card 4: Goal Adherence */}
            <div className="wellness-card" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Goal Adherence
                </span>
                <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: '#E1F4EA', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}>
                  <CheckCircle2 size={15} />
                </div>
              </div>
              <div style={{ fontSize: '1.6rem', fontWeight: '800', color: 'var(--primary)', lineHeight: 1.2 }}>
                {Math.round(summary.goal_adherence_pct || 0)}%
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                <span>Target range (±15%)</span>
                <span style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
                  {summary.total_tracked_days || 0} tracked days
                </span>
              </div>
            </div>
          </div>

          {/* 3. Section 1: Calorie Intake Analysis */}
          <div className="wellness-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                  1. Calorie Intake Analysis
                </h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Daily consumed calories vs recommended target ({summary.target_calories || 2000} kcal)
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: 'var(--calorie-orange)' }} />
                  <span>On Target</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: '#DC4C4C' }} />
                  <span>Over Target</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: '#D8E2DC' }} />
                  <span>Unlogged</span>
                </div>
              </div>
            </div>

            <div style={{ height: '300px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={caloriesSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                  <XAxis dataKey="display_date" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <Tooltip content={<CustomChartTooltip unit="kcal" target={summary.target_calories || 2000} />} />
                  <ReferenceLine y={summary.target_calories || 2000} stroke="var(--success)" strokeDasharray="4 4" strokeWidth={2} label={{ value: 'Target', position: 'insideTopRight', fill: 'var(--success)', fontSize: 11 }} />
                  <Bar
                    dataKey="consumed"
                    name="Consumed Calories"
                    radius={[4, 4, 0, 0]}
                  >
                    {caloriesSeries.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={
                          !entry.is_tracked ? 'var(--border-glass)' :
                          entry.status === 'over' ? 'var(--danger)' :
                          entry.status === 'under' ? 'var(--warning)' :
                          'var(--calorie-orange)'
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Grounded Calorie Insight */}
            <div style={{ marginTop: '14px', padding: '10px 14px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              <Info size={16} color="var(--primary)" />
              <span>{analyticsData?.calorie_insight || `Your average intake is ${summary.avg_calories || 0} kcal per day against your ${summary.target_calories || 2000} kcal target.`}</span>
            </div>
          </div>

          {/* 4. Section 2 & Section 3: Hydration & Macronutrient Breakdown (2-Column Grid) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))', gap: '20px' }}>
            
            {/* Hydration Analysis */}
            <div className="wellness-card" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                    2. Hydration Analysis
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Daily water intake vs target ({Number(summary.target_water_liters || 2.5).toFixed(1)}L)
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', fontWeight: '700', color: 'var(--hydration-cyan)' }}>
                  Avg: {Number(summary.avg_water_liters || 0).toFixed(1)} L/day
                </div>
              </div>

              <div style={{ height: '260px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={hydrationSeries} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                    <XAxis dataKey="display_date" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <Tooltip content={<CustomChartTooltip unit="L" target={Number(summary.target_water_liters || 2.5).toFixed(1)} />} />
                    <ReferenceLine y={Number(summary.target_water_liters || 2.5)} stroke="var(--hydration-cyan)" strokeDasharray="3 3" strokeWidth={2} />
                    <Bar dataKey="consumed_liters" name="Water (Liters)" fill="var(--hydration-cyan)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                <span>Achieved goal: <strong style={{ color: 'var(--text-primary)' }}>{hydrationSummary.days_goal_achieved || 0} of {hydrationSummary.total_days || summary.total_period_days || 7} days</strong></span>
                <span>Best day: <strong style={{ color: 'var(--text-primary)' }}>{hydrationSummary.best_day?.display_date ? `${hydrationSummary.best_day.display_date} (${hydrationSummary.best_day.liters}L)` : 'Consistent'}</strong></span>
              </div>
            </div>

            {/* Macronutrient Breakdown */}
            <div className="wellness-card" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                    3. Macronutrient Breakdown
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Protein, Carbohydrates, and Fats distribution
                  </span>
                </div>
                {/* Toggle View Mode */}
                <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-subtle)', padding: '2px', borderRadius: 'var(--radius-sm)' }}>
                  <button
                    type="button"
                    onClick={() => setMacroViewMode('daily')}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '4px',
                      border: 'none',
                      background: macroViewMode === 'daily' ? 'var(--bg-active-tab, #FFFFFF)' : 'transparent',
                      color: macroViewMode === 'daily' ? 'var(--primary)' : 'var(--text-secondary)',
                      fontWeight: '700',
                      fontSize: '0.74rem',
                      cursor: 'pointer'
                    }}
                  >
                    Daily
                  </button>
                  <button
                    type="button"
                    onClick={() => setMacroViewMode('average')}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '4px',
                      border: 'none',
                      background: macroViewMode === 'average' ? 'var(--bg-active-tab, #FFFFFF)' : 'transparent',
                      color: macroViewMode === 'average' ? 'var(--primary)' : 'var(--text-secondary)',
                      fontWeight: '700',
                      fontSize: '0.74rem',
                      cursor: 'pointer'
                    }}
                  >
                    Split %
                  </button>
                </div>
              </div>

              {macroViewMode === 'daily' ? (
                <div style={{ height: '260px', width: '100%' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={macrosSeries} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                      <XAxis dataKey="display_date" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                      <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                      <Tooltip content={<CustomChartTooltip unit="g" />} />
                      <Legend iconSize={10} wrapperStyle={{ fontSize: '0.76rem', paddingTop: '8px' }} />
                      <Bar dataKey="protein_g" name="Protein (g)" stackId="a" fill="#60A5FA" />
                      <Bar dataKey="carbs_g" name="Carbs (g)" stackId="a" fill="#FBBF24" />
                      <Bar dataKey="fat_g" name="Fat (g)" stackId="a" fill="#F472B6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div style={{ height: '260px', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={macroPieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={90}
                        paddingAngle={4}
                        dataKey="value"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {macroPieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value, name, item) => [`${item.payload.grams}g (${value}%)`, name]} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}

              <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-around', fontSize: '0.78rem', color: 'var(--text-secondary)', borderTop: '1px solid var(--border-glass)', paddingTop: '10px' }}>
                <span>Protein: <strong style={{ color: '#60A5FA' }}>{Math.round(macroAverages.avg_protein_g || 0)}g</strong></span>
                <span>Carbs: <strong style={{ color: '#FBBF24' }}>{Math.round(macroAverages.avg_carbs_g || 0)}g</strong></span>
                <span>Fat: <strong style={{ color: '#F472B6' }}>{Math.round(macroAverages.avg_fat_g || 0)}g</strong></span>
                <span>Fiber: <strong style={{ color: 'var(--macro-fiber)' }}>{Math.round(macroAverages.avg_fiber_g || 0)}g</strong></span>
              </div>
            </div>
          </div>

          {/* 5. Section 4 & Section 5: Protein Progress & Activity / Energy Burned (2-Column Grid) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))', gap: '20px' }}>
            
            {/* Protein Progress */}
            <div className="wellness-card" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                    4. Protein Progress
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Daily protein vs target ({Math.round(summary.target_protein || 110)}g)
                  </span>
                </div>
                <div style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  background: (summary.avg_protein || 0) >= (summary.target_protein || 110) * 0.9 ? 'var(--success-bg)' : 'var(--warning-bg)',
                  color: (summary.avg_protein || 0) >= (summary.target_protein || 110) * 0.9 ? 'var(--success)' : 'var(--warning)',
                  fontWeight: '700',
                  fontSize: '0.78rem'
                }}>
                  {proteinSummary.achievement_pct || 0}% Target Met
                </div>
              </div>

              <div style={{ height: '260px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={proteinSeries} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                    <XAxis dataKey="display_date" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <Tooltip content={<CustomChartTooltip unit="g" target={Math.round(summary.target_protein || 110)} />} />
                    <ReferenceLine y={Math.round(summary.target_protein || 110)} stroke="#60A5FA" strokeDasharray="4 4" strokeWidth={2} />
                    <Bar dataKey="consumed_g" name="Protein (g)" fill="#60A5FA" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div style={{ marginTop: '12px', fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
                <span>Days target met: <strong style={{ color: 'var(--text-primary)' }}>{proteinSummary.days_met || 0} of {proteinSummary.total_days || summary.total_period_days || 7} days</strong></span>
                <span>Average: <strong style={{ color: 'var(--text-primary)' }}>{Math.round(summary.avg_protein || 0)}g / day</strong></span>
              </div>
            </div>

            {/* Activity & Energy Burned */}
            <div className="wellness-card" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                    5. Activity & Calories Burned
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Active calories burned through exercise
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', fontWeight: '700', color: '#EA580C' }}>
                  Total: {Math.round(activitySummary.total_calories_burned || 0)} kcal
                </div>
              </div>

              <div style={{ height: '260px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={activitySeries} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                    <XAxis dataKey="display_date" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <Tooltip content={<CustomChartTooltip unit="kcal" />} />
                    <Bar dataKey="calories_burned" name="Burned (kcal)" fill="#F97316" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div style={{ marginTop: '12px', fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
                <span>Active duration: <strong style={{ color: 'var(--text-primary)' }}>{activitySummary.total_duration_minutes || 0} mins</strong></span>
                <span>Avg burned: <strong style={{ color: 'var(--text-primary)' }}>{Math.round(activitySummary.avg_calories_burned || 0)} kcal/day</strong></span>
              </div>
            </div>
          </div>

          {/* 6. Section 6: Calorie Balance (Intake vs Burned vs Net) */}
          <div className="wellness-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                  6. Calorie Balance
                </h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Calorie intake vs calories burned vs net energy balance
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: 'var(--calorie-orange)' }} />
                  <span>Intake</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: '#F97316' }} />
                  <span>Burned</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <div style={{ width: '10px', height: '2px', background: 'var(--primary)' }} />
                  <span>Net Calories</span>
                </div>
              </div>
            </div>

            <div style={{ height: '300px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={balanceSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                  <XAxis dataKey="display_date" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <Tooltip content={<CustomChartTooltip unit="kcal" />} />
                  <ReferenceLine y={summary.target_calories || 2000} stroke="#10B981" strokeDasharray="3 3" />
                  <Bar dataKey="intake" name="Intake (kcal)" fill="var(--calorie-orange)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="burned" name="Burned (kcal)" fill="#F97316" radius={[4, 4, 0, 0]} />
                  <Line type="monotone" dataKey="net" name="Net Calories" stroke="var(--primary)" strokeWidth={3} dot={{ r: 4, fill: 'var(--primary)' }} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 7. Section 7: Weight Progress */}
          <div className="wellness-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                  7. Weight Progress
                </h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Historical body weight tracking vs target weight
                </span>
              </div>
              {weightProgress.has_history && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.8rem' }}>
                  <span>Current: <strong style={{ color: 'var(--text-primary)' }}>{weightProgress.current_weight_kg} kg</strong></span>
                  {weightProgress.target_weight_kg && (
                    <span>Target: <strong style={{ color: 'var(--primary)' }}>{weightProgress.target_weight_kg} kg</strong></span>
                  )}
                  {weightProgress.weight_change_kg !== null && weightProgress.weight_change_kg !== 0 && (
                    <span style={{
                      fontWeight: '700',
                      color: weightProgress.weight_change_kg < 0 ? 'var(--primary)' : 'var(--calorie-orange)'
                    }}>
                      {weightProgress.weight_change_kg > 0 ? `+${weightProgress.weight_change_kg}` : weightProgress.weight_change_kg} kg
                    </span>
                  )}
                </div>
              )}
            </div>

            {weightProgress.has_history && weightProgress.history.length > 0 ? (
              <div style={{ height: '260px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={weightProgress.history} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                    <XAxis dataKey="display_date" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <YAxis domain={['auto', 'auto']} tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                    <Tooltip content={<CustomChartTooltip unit="kg" target={weightProgress.target_weight_kg} />} />
                    {weightProgress.target_weight_kg && (
                      <ReferenceLine y={weightProgress.target_weight_kg} stroke="#10B981" strokeDasharray="3 3" label={{ value: 'Target', fill: '#10B981', fontSize: 11 }} />
                    )}
                    <Line type="monotone" dataKey="weight_kg" name="Weight (kg)" stroke="#8B5CF6" strokeWidth={3} dot={{ r: 5, fill: '#8B5CF6' }} activeDot={{ r: 7 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div style={{ padding: '36px 20px', textAlign: 'center', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
                <Scale size={36} color="var(--text-muted)" style={{ margin: '0 auto 10px auto' }} />
                <h4 style={{ fontSize: '1rem', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>
                  No weight history recorded yet
                </h4>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', margin: '4px 0 16px 0' }}>
                  Log your body weight periodically in your profile to visualize your weight trend over time.
                </p>
                <button
                  type="button"
                  onClick={() => setTab('profile')}
                  className="btn-secondary"
                  style={{ padding: '8px 18px', fontSize: '0.84rem' }}
                >
                  <Scale size={15} /> Update Weight in Profile
                </button>
              </div>
            )}
          </div>

          {/* 8. Grounded Nutrition Insights Cards */}
          {insights.length > 0 && (
            <div className="wellness-card" style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px', color: 'var(--primary)' }}>
                <Sparkles size={20} />
                <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                  Dietary Intelligence & Insights
                </h3>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                {insights.map((insight, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '14px 16px',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--bg-subtle)',
                      border: '1px solid var(--border-glass)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '10px',
                      fontSize: '0.84rem',
                      color: 'var(--text-primary)',
                      lineHeight: '1.4'
                    }}
                  >
                    <CheckCircle2 size={16} color="var(--primary)" style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span>{insight}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

        </>
      )}

    </div>
  );
};
