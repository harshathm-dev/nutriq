import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import {
  Calendar, ChevronLeft, ChevronRight, Flame, Droplets, Utensils,
  Activity, Award, AlertTriangle, CheckCircle2, ChevronDown, ChevronUp,
  Plus, Info, Sparkles, RefreshCw, AlertCircle, Download, Wifi, WifiOff,
  Trash2, Edit2
} from 'lucide-react';
import { getToday, addDays, subtractDays, formatDate, isToday as checkIsToday, isFuture as checkIsFuture } from '../utils/dateUtils';
import { SmartNutritionRecommendations } from '../components/SmartNutritionRecommendations';

export const DailySummaryPage = () => {
  const { targets, profile, setTab, navigate, isOnline, triggerSync, syncPendingCount } = useStore();
  const [selectedDate, setSelectedDate] = useState(getToday());
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedMeals, setExpandedMeals] = useState({
    breakfast: true,
    lunch: true,
    snack: true,
    dinner: true
  });

  const isToday = checkIsToday(selectedDate);
  const isFuture = checkIsFuture(selectedDate);

  useEffect(() => {
    fetchSummary(selectedDate);
  }, [selectedDate]);

  const fetchSummary = async (dateStr) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDailySummary(dateStr);
      setSummaryData(data);
    } catch (err) {
      console.warn("Failed to fetch daily summary:", err);
      setError("Unable to load daily summary. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handlePrevDay = () => {
    setSelectedDate(prev => subtractDays(prev, 1));
  };

  const handleNextDay = () => {
    setSelectedDate(prev => addDays(prev, 1));
  };

  const toggleMealExpand = (mealSlot) => {
    setExpandedMeals(prev => ({ ...prev, [mealSlot]: !prev[mealSlot] }));
  };

  const calories = summaryData?.calories || {
    target: targets?.target_calories || profile?.calorie_target || 2000,
    consumed: 0,
    remaining: targets?.target_calories || profile?.calorie_target || 2000,
    burned: 0,
    net: 0,
    is_over: false,
    over_amount: 0
  };

  const macros = summaryData?.macros || {
    protein: { target: targets?.protein_g || profile?.protein_target_g || 100, consumed: 0, percentage: 0 },
    carbohydrates: { target: targets?.carbs_g || 250, consumed: 0, percentage: 0 },
    fat: { target: targets?.fat_g || 60, consumed: 0, percentage: 0 },
    fiber: { target: targets?.fiber_g || 28, consumed: 0, percentage: 0 }
  };

  const hydration = summaryData?.hydration || {
    target_ml: targets?.water_ml || 2500,
    consumed_ml: 0,
    remaining_ml: targets?.water_ml || 2500,
    percentage: 0,
    is_zero: true
  };

  const meals = summaryData?.meals || {
    breakfast: { logged: false, status_label: "Not logged", items: [] },
    lunch: { logged: false, status_label: "Not logged", items: [] },
    snack: { logged: false, status_label: "Not logged", items: [] },
    dinner: { logged: false, status_label: "Not logged", items: [] },
    logged_count: 0,
    total_slots: 4
  };

  const formatLiters = (ml) => {
    if (!ml || isNaN(ml) || ml <= 0) return '0.0';
    const l = ml / 1000;
    if (Number.isInteger(l)) return `${l.toFixed(1)}`;
    const fixed = l.toFixed(2);
    return fixed.endsWith('0') ? l.toFixed(1) : fixed;
  };

  const getProteinSuggestions = (dietaryPreference) => {
    const pref = (dietaryPreference || '').toLowerCase();
    if (pref.includes('vegan')) {
      return ['Soy / Tofu', 'Sprouts & Microgreens', 'Lentils / Dal', 'Chickpeas & Beans', 'Seeds & Nuts'];
    }
    if (pref.includes('veg') && !pref.includes('non')) {
      return ['Paneer', 'Curd / Greek Yogurt', 'Dal / Lentils', 'Sprouts', 'Soy / Tofu'];
    }
    return ['Eggs', 'Paneer', 'Curd / Greek Yogurt', 'Dal / Sprouts', 'Chicken / Fish', 'Soy / Tofu'];
  };

  // Generate dynamic nutrition warnings based on current daily metrics and targets
  const getNutritionWarnings = () => {
    if (isFuture) {
      return [{
        type: 'info',
        title: 'Future Date Selected',
        message: 'Log meals on this date to view your actual recorded nutrition and calorie insights.',
        current: null,
        target: null
      }];
    }

    const hasMeals = meals.logged_count > 0 || (calories.consumed > 0);
    if (!hasMeals) {
      return [{
        type: 'info',
        title: 'No Meals Recorded For This Date',
        message: 'Start logging your meals to track your daily energy and macronutrient balance.',
        current: null,
        target: null
      }];
    }

    const warnings = [];
    const consumedCal = calories.consumed || 0;
    const targetCal = calories.target || 2000;
    const remainingCal = Math.max(0, targetCal - consumedCal);
    const overCal = Math.max(0, consumedCal - targetCal);

    const consumedPro = macros.protein?.consumed || 0;
    const targetPro = macros.protein?.target || 100;

    const goal = (profile?.fitness_goal || 'weight_loss').toLowerCase();
    const dietaryPref = profile?.dietary_preference || 'general';

    // 1. Low Calorie / Safety Deficit Warning
    const isSevereDeficit = consumedCal > 0 && consumedCal < targetCal * 0.65;
    const isMeaningfullyLowCal = consumedCal > 0 && consumedCal < targetCal * 0.78;

    if (goal.includes('weight_loss') || goal.includes('fat_loss')) {
      if (isSevereDeficit) {
        warnings.push({
          type: 'warning',
          title: '⚠ Intake May Be Too Low',
          current: `${Math.round(consumedCal)} kcal`,
          target: `${Math.round(targetCal)} kcal`,
          remaining: `${Math.round(remainingCal)} kcal remaining`,
          message: 'Your current calorie intake is considerably below your recommended target. A very large calorie deficit may make it harder to maintain adequate nutrition and energy. Consider choosing balanced meals rather than drastically reducing food intake.',
          suggestions: null
        });
      } else if (isMeaningfullyLowCal) {
        warnings.push({
          type: 'warning',
          title: '⚠ Low Calorie Intake',
          current: `${Math.round(consumedCal)} kcal`,
          target: `${Math.round(targetCal)} kcal`,
          remaining: `${Math.round(remainingCal)} kcal remaining`,
          message: 'Your current intake is significantly below your daily calorie target. Try to consume enough nutritious food to meet your energy needs.',
          suggestions: null
        });
      }
    } else {
      if (isMeaningfullyLowCal) {
        warnings.push({
          type: 'warning',
          title: '⚠ Low Calorie Intake',
          current: `${Math.round(consumedCal)} kcal`,
          target: `${Math.round(targetCal)} kcal`,
          remaining: `${Math.round(remainingCal)} kcal remaining`,
          message: 'Your current intake is significantly below your daily calorie target. Try to consume enough nutritious food to meet your energy needs.',
          suggestions: null
        });
      }
    }

    // 2. High Calorie Warning
    if (consumedCal > targetCal * 1.15 && consumedCal > targetCal + 80) {
      warnings.push({
        type: 'warning',
        title: '⚠ Calorie Intake Above Target',
        current: `${Math.round(consumedCal)} kcal`,
        target: `${Math.round(targetCal)} kcal`,
        remaining: `+${Math.round(overCal)} kcal over`,
        message: "Your energy intake has exceeded today's calorie budget. Stay hydrated and balance your remaining meals with lighter options.",
        suggestions: null
      });
    }

    // 3. Low Protein Warning
    const isLowProtein = consumedPro < targetPro * 0.7 && consumedCal > 250;
    if (isLowProtein) {
      warnings.push({
        type: 'warning',
        title: '⚠ Low Protein Intake',
        current: `${Math.round(consumedPro)}g`,
        target: `${Math.round(targetPro)}g`,
        remaining: `${Math.round(Math.max(0, targetPro - consumedPro))}g needed`,
        message: 'Your protein intake is currently below your daily target. Consider adding protein-rich foods to your next meal.',
        suggestions: getProteinSuggestions(dietaryPref)
      });
    }

    // 4. Positive On-Track State
    if (warnings.length === 0) {
      warnings.push({
        type: 'positive',
        title: '✓ Nutrition On Track',
        current: `${Math.round(consumedCal)} kcal`,
        target: `${Math.round(targetCal)} kcal`,
        remaining: null,
        message: "Your calorie and protein intake are currently aligned with today's targets. Great job maintaining nutritional balance!",
        suggestions: null
      });
    }

    return warnings;
  };

  const nutritionWarnings = getNutritionWarnings();

  return (
    <div className="page-container">
      
      {/* 1. Header & Date Navigation Card */}
      <div className="wellness-card" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)', marginBottom: '4px' }}>
              <Calendar size={20} />
              <h2 style={{ fontSize: '1.5rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>Daily Summary</h2>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', margin: 0 }}>
              Grounded, verifiable overview of your actual recorded nutrition, hydration, and meals.
            </p>
          </div>

          {/* Date Selector Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-subtle)', padding: '6px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-glass)' }}>
            <button
              type="button"
              onClick={handlePrevDay}
              className="btn-secondary"
              style={{ padding: '6px 10px', fontSize: '0.8rem' }}
              title="Previous Day"
            >
              <ChevronLeft size={16} />
            </button>
            <span style={{ fontSize: '0.88rem', fontWeight: '800', color: 'var(--text-primary)', minWidth: '140px', textAlign: 'center' }}>
              {formatDate(selectedDate)}
            </span>
            <button
              type="button"
              onClick={handleNextDay}
              className="btn-secondary"
              style={{ padding: '6px 10px', fontSize: '0.8rem' }}
              title="Next Day"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="wellness-card" style={{ padding: '48px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <RefreshCw size={24} className="spin" style={{ margin: '0 auto 12px auto', color: 'var(--primary)' }} />
          <div>Loading daily summary...</div>
        </div>
      ) : error ? (
        <div className="wellness-card" style={{ padding: '36px', textAlign: 'center' }}>
          <AlertCircle size={32} color="#DC4C4C" style={{ margin: '0 auto 12px auto' }} />
          <h3 style={{ fontSize: '1.1rem', fontWeight: '800', color: 'var(--text-primary)', margin: '0 0 6px 0' }}>
            {error}
          </h3>
          <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', margin: '0 0 16px 0' }}>
            Could not retrieve summary metrics for this date.
          </p>
          <button
            type="button"
            onClick={() => fetchSummary(selectedDate)}
            className="btn-primary"
            style={{ padding: '8px 18px', fontSize: '0.84rem' }}
          >
            Try Again
          </button>
        </div>
      ) : (
        <>
          {/* 2. Key Energy & Hydration Metrics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            <div className="wellness-card" style={{ padding: '20px' }}>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>Energy Consumed</span>
              <div style={{ fontSize: '1.45rem', fontWeight: '800', color: 'var(--calorie-orange)', margin: '4px 0' }}>
                {Math.round(calories.consumed || 0)} <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>/ {Math.round(calories.target || 2000)} kcal</span>
              </div>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {Math.round(calories.remaining || 0)} kcal remaining
              </span>
            </div>

            <div className="wellness-card" style={{ padding: '20px' }}>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>Protein Intake</span>
              <div style={{ fontSize: '1.45rem', fontWeight: '800', color: 'var(--macro-protein)', margin: '4px 0' }}>
                {Math.round(macros.protein?.consumed || 0)}g <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>/ {Math.round(macros.protein?.target || 100)}g</span>
              </div>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {Math.round(macros.protein?.percentage || (macros.protein?.target > 0 ? (macros.protein.consumed / macros.protein.target) * 100 : 0))}% of goal
              </span>
            </div>

            <div className="wellness-card" style={{ padding: '20px' }}>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>Hydration</span>
              <div style={{ fontSize: '1.45rem', fontWeight: '800', color: 'var(--hydration-cyan)', margin: '4px 0' }}>
                {formatLiters(hydration.consumed_ml || 0)} <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>/ {formatLiters(hydration.target_ml || 2500)} L</span>
              </div>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                {Math.round(hydration.percentage || (hydration.target_ml > 0 ? (hydration.consumed_ml / hydration.target_ml) * 100 : 0))}% of daily goal
              </span>
            </div>

            <div className="wellness-card" style={{ padding: '20px' }}>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>Logged Meals</span>
              <div style={{ fontSize: '1.45rem', fontWeight: '800', color: 'var(--primary)', margin: '4px 0' }}>
                {meals.logged_count || 0} <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>/ 4 slots</span>
              </div>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Journal completion
              </span>
            </div>
          </div>

          {/* 3. Nutrition Insights & Dynamic Warnings */}
          <div className="wellness-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <Sparkles size={18} color="var(--primary)" />
              <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                Nutrition Insights
              </h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {nutritionWarnings.map((w, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '16px 18px',
                    borderRadius: 'var(--radius-md)',
                    background: w.type === 'positive' ? 'rgba(22, 134, 95, 0.08)' : w.type === 'info' ? 'var(--bg-subtle)' : 'rgba(245, 158, 11, 0.08)',
                    border: w.type === 'positive' ? '1px solid rgba(22, 134, 95, 0.25)' : w.type === 'info' ? '1px solid var(--border-glass)' : '1px solid rgba(245, 158, 11, 0.3)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {w.type === 'positive' ? (
                        <CheckCircle2 size={18} color="var(--primary)" />
                      ) : w.type === 'info' ? (
                        <Info size={18} color="var(--text-secondary)" />
                      ) : (
                        <AlertTriangle size={18} color="#D97706" />
                      )}
                      <span style={{
                        fontSize: '0.92rem',
                        fontWeight: '800',
                        color: w.type === 'positive' ? 'var(--primary)' : w.type === 'info' ? 'var(--text-primary)' : '#B45309'
                      }}>
                        {w.title}
                      </span>
                    </div>

                    {w.current && w.target && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className="badge" style={{
                          background: 'var(--bg-card)',
                          color: 'var(--text-primary)',
                          fontSize: '0.74rem',
                          padding: '3px 8px',
                          fontWeight: '700'
                        }}>
                          {w.current} / {w.target}
                        </span>
                        {w.remaining && (
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: '600' }}>
                            ({w.remaining})
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: '1.45' }}>
                    {w.message}
                  </p>

                  {w.suggestions && w.suggestions.length > 0 && (
                    <div style={{ marginTop: '4px', paddingTop: '8px', borderTop: '1px dashed rgba(245, 158, 11, 0.2)' }}>
                      <span style={{ fontSize: '0.76rem', fontWeight: '700', color: 'var(--text-primary)', display: 'block', marginBottom: '6px' }}>
                        Consider adding protein-rich foods such as:
                      </span>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {w.suggestions.map((sug, sIdx) => (
                          <span
                            key={sIdx}
                            className="badge"
                            style={{
                              background: 'var(--bg-card)',
                              color: 'var(--primary)',
                              fontSize: '0.72rem',
                              padding: '2px 8px',
                              border: '1px solid var(--border-glass)'
                            }}
                          >
                            • {sug}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 4. Smart Nutrition Recommendations */}
          <SmartNutritionRecommendations targetDate={selectedDate} />

          {/* 5. Meal Slot Status & Nutrition */}
          <div className="wellness-card" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                  Meal Slot Status & Nutrition
                </h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Itemized food journal with macro breakdowns for each meal
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {[
                { key: 'breakfast', label: 'Breakfast', icon: '🍳' },
                { key: 'lunch', label: 'Lunch', icon: '☀️' },
                { key: 'snack', label: 'Evening Snack', icon: '🍇' },
                { key: 'dinner', label: 'Dinner', icon: '🌙' }
              ].map(({ key, label, icon }) => {
                const slot = meals[key] || { logged: false, items: [] };
                const isExpanded = expandedMeals[key];
                const items = Array.isArray(slot.items) ? slot.items : [];
                const itemCount = items.length;
                const isLogged = slot.logged && itemCount > 0;
                const slotCal = Math.round(slot.total_calories || slot.calories || items.reduce((acc, it) => acc + (parseFloat(it.calories) || 0), 0));
                const slotPro = Math.round((slot.total_protein_g || slot.protein_g || items.reduce((acc, it) => acc + (parseFloat(it.protein_g) || 0), 0)) * 10) / 10;
                const slotCarb = Math.round((slot.total_carbs_g || slot.carbs_g || items.reduce((acc, it) => acc + (parseFloat(it.carbs_g) || 0), 0)) * 10) / 10;
                const slotFat = Math.round((slot.total_fat_g || slot.fat_g || items.reduce((acc, it) => acc + (parseFloat(it.fat_g) || 0), 0)) * 10) / 10;
                const slotFib = Math.round((slot.total_fiber_g || slot.fiber_g || items.reduce((acc, it) => acc + (parseFloat(it.fiber_g) || 0), 0)) * 10) / 10;

                return (
                  <div
                    key={key}
                    style={{
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--bg-subtle)',
                      border: isLogged ? '1px solid var(--border-glass)' : '1px dashed var(--border-glass)',
                      overflow: 'hidden',
                      transition: 'all 0.16s ease'
                    }}
                  >
                    {/* Slot Header */}
                    <div
                      onClick={() => toggleMealExpand(key)}
                      style={{
                        padding: '14px 18px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        flexWrap: 'wrap',
                        gap: '12px',
                        cursor: 'pointer',
                        background: isExpanded ? 'rgba(22, 124, 90, 0.03)' : 'transparent',
                        userSelect: 'none'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <span style={{ fontSize: '1.4rem' }}>{icon}</span>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <h4 style={{ fontSize: '1rem', fontWeight: '800', color: 'var(--text-primary)', margin: 0 }}>
                              {label}
                            </h4>
                            {isLogged ? (
                              <span className="badge badge-emerald" style={{ fontSize: '0.68rem', padding: '1px 7px' }}>
                                ✓ Completed
                              </span>
                            ) : (
                              <span className="badge" style={{ background: 'var(--bg-card)', color: 'var(--text-muted)', fontSize: '0.68rem', padding: '1px 7px' }}>
                                ○ Not Logged
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                            {isLogged ? (
                              <span>
                                {itemCount} {itemCount === 1 ? 'item' : 'items'} recorded • <strong style={{ color: 'var(--calorie-orange)' }}>{slotCal} kcal</strong>
                              </span>
                            ) : (
                              <span style={{ color: 'var(--text-muted)' }}>No items recorded yet</span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        {!isLogged && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/log-meal?date=${selectedDate}&meal_type=${key}`);
                            }}
                            className="btn-secondary"
                            style={{ padding: '5px 12px', fontSize: '0.78rem' }}
                          >
                            <Plus size={14} /> Log {label}
                          </button>
                        )}
                        <div style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', padding: '4px' }}>
                          {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </div>
                      </div>
                    </div>

                    {/* Expanded Content */}
                    {isExpanded && (
                      <div style={{
                        padding: '14px 18px 16px 18px',
                        borderTop: '1px solid var(--border-glass)',
                        background: 'var(--bg-card)'
                      }}>
                        {isLogged ? (
                          <>
                            {/* Food Items List */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '14px' }}>
                              {items.map((item, iIdx) => {
                                const foodName = item.food_name || item.name || item.title || 'Food Item';
                                const quantity = item.quantity || item.amount || 1;
                                const unit = item.serving_unit || item.unit || 'serving';
                                const cal = Math.round(item.calories || 0);

                                let quantityLabel = `${quantity}x ${foodName}`;
                                if (unit && unit !== 'serving' && unit !== 'servings' && unit !== 'item' && unit !== 'portion') {
                                  quantityLabel = `${quantity} ${unit} ${foodName}`;
                                }

                                return (
                                  <div
                                    key={iIdx}
                                    style={{
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'space-between',
                                      padding: '8px 12px',
                                      background: 'var(--bg-subtle)',
                                      borderRadius: 'var(--radius-sm)',
                                      border: '1px solid var(--border-glass)',
                                      fontSize: '0.86rem'
                                    }}
                                  >
                                    <span style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
                                      • {quantityLabel}
                                    </span>
                                    <span style={{ fontWeight: '800', color: 'var(--calorie-orange)' }}>
                                      {cal} kcal
                                    </span>
                                  </div>
                                );
                              })}
                            </div>

                            {/* Meal Slot Macros Footer */}
                            <div style={{
                              display: 'flex',
                              flexWrap: 'wrap',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: '8px',
                              padding: '10px 14px',
                              borderRadius: 'var(--radius-sm)',
                              background: 'rgba(22, 124, 90, 0.04)',
                              border: '1px solid rgba(22, 124, 90, 0.12)',
                              fontSize: '0.8rem'
                            }}>
                              <span style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
                                Total: <strong style={{ color: 'var(--calorie-orange)' }}>{slotCal} kcal</strong>
                              </span>
                              <span style={{ color: 'var(--text-secondary)' }}>
                                Protein: <strong style={{ color: 'var(--macro-protein)' }}>{slotPro}g</strong> •
                                Carbs: <strong style={{ color: 'var(--macro-carbs, #3B82F6)' }}>{slotCarb}g</strong> •
                                Fat: <strong style={{ color: 'var(--macro-fat, #EAB308)' }}>{slotFat}g</strong> •
                                Fiber: <strong style={{ color: 'var(--macro-fiber, #10B981)' }}>{slotFib}g</strong>
                              </span>
                            </div>
                          </>
                        ) : (
                          <div style={{ textAlign: 'center', padding: '16px', color: 'var(--text-muted)', fontSize: '0.84rem' }}>
                            No items recorded for {label.toLowerCase()}.
                            <div style={{ marginTop: '8px' }}>
                              <button
                                type="button"
                                onClick={() => navigate(`/log-meal?date=${selectedDate}&meal_type=${key}`)}
                                className="btn-secondary"
                                style={{ padding: '5px 14px', fontSize: '0.78rem', margin: '0 auto' }}
                              >
                                <Plus size={14} /> Add food to {label}
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
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
