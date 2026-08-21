import React, { useState, useEffect, useRef } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import {
  Calendar, ChevronLeft, ChevronRight, Utensils, Flame, Droplets,
  Activity, Plus, Trash2, Edit2, Clock, CheckCircle2, AlertCircle,
  TrendingUp, RefreshCw, X, Check, Save
} from 'lucide-react';
import {
  getToday,
  addDays,
  subtractDays,
  formatDate,
  isToday as checkIsToday,
  isFuture as checkIsFuture,
  formatTime
} from '../utils/dateUtils';

export const MealHistoryPage = () => {
  const { setTab, navigate, refreshAllData } = useStore();
  
  const getInitialDate = () => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const qDate = params.get('date');
      if (qDate && /^\d{4}-\d{2}-\d{2}$/.test(qDate)) {
        return qDate;
      }
    }
    return getToday();
  };

  const [selectedDate, setSelectedDate] = useState(getInitialDate());
  const [historyData, setHistoryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingMeal, setEditingMeal] = useState(null);
  const [editMealType, setEditMealType] = useState('breakfast');
  const [editItems, setEditItems] = useState([]);
  const [savingEdit, setSavingEdit] = useState(false);

  const activeRequestIdRef = useRef(0);

  const isSelectedToday = checkIsToday(selectedDate);
  const isSelectedFuture = checkIsFuture(selectedDate);

  useEffect(() => {
    fetchHistory(selectedDate);
  }, [selectedDate]);

  const fetchHistory = async (dateStr) => {
    const reqId = ++activeRequestIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMealHistory(dateStr);
      if (reqId === activeRequestIdRef.current) {
        setHistoryData(data);
      }
    } catch (err) {
      console.warn("Failed to fetch meal history:", err);
      if (reqId === activeRequestIdRef.current) {
        setError("Unable to load meal history for this date.");
      }
    } finally {
      if (reqId === activeRequestIdRef.current) {
        setLoading(false);
      }
    }
  };

  const handlePrevDay = () => {
    setSelectedDate(prev => subtractDays(prev, 1));
  };

  const handleNextDay = () => {
    setSelectedDate(prev => addDays(prev, 1));
  };

  const handleToday = () => {
    setSelectedDate(getToday());
  };

  const handleDeleteMeal = async (mealId) => {
    if (!window.confirm("Are you sure you want to delete this meal record?")) {
      return;
    }
    try {
      await api.deleteMeal(mealId);
      await fetchHistory(selectedDate);
      await refreshAllData();
    } catch (err) {
      console.error("Failed to delete meal:", err);
      alert("Unable to delete meal. Please try again.");
    }
  };

  const handleStartEditMeal = (meal) => {
    setEditingMeal(meal);
    setEditMealType(meal.meal_type || 'breakfast');
    setEditItems((meal.items || []).map(i => ({
      ...i,
      name: i.food_name || i.name || 'Food item',
      food_name: i.food_name || i.name || 'Food item',
      portion: Number(i.quantity !== undefined && i.quantity !== null ? i.quantity : (i.portion !== undefined && i.portion !== null ? i.portion : 1)),
      quantity: Number(i.quantity !== undefined && i.quantity !== null ? i.quantity : (i.portion !== undefined && i.portion !== null ? i.portion : 1)),
      calories: Number(i.calories || 0),
      protein: Number(i.protein_g !== undefined ? i.protein_g : (i.protein || 0)),
      protein_g: Number(i.protein_g !== undefined ? i.protein_g : (i.protein || 0)),
      carbs: Number(i.carbs_g !== undefined ? i.carbs_g : (i.carbs || 0)),
      carbs_g: Number(i.carbs_g !== undefined ? i.carbs_g : (i.carbs || 0)),
      fat: Number(i.fat_g !== undefined ? i.fat_g : (i.fat || 0)),
      fat_g: Number(i.fat_g !== undefined ? i.fat_g : (i.fat || 0))
    })));
  };

  const handleItemQtyChange = (index, newQty) => {
    const qty = Math.max(0.1, parseFloat(newQty) || 0.1);
    setEditItems(prev => {
      const updated = [...prev];
      const item = updated[index];
      const baseMult = item.portion > 0 ? (qty / item.portion) : 1;
      updated[index] = {
        ...item,
        portion: qty,
        calories: Math.round((item.calories * baseMult) * 10) / 10,
        protein: Math.round((item.protein * baseMult) * 10) / 10,
        carbs: Math.round((item.carbs * baseMult) * 10) / 10,
        fat: Math.round((item.fat * baseMult) * 10) / 10
      };
      return updated;
    });
  };

  const handleSaveEditMeal = async () => {
    if (!editingMeal) return;
    setSavingEdit(true);
    try {
      await api.updateMeal(editingMeal.id, {
        meal_type: editMealType,
        items: editItems
      });
      setEditingMeal(null);
      await fetchHistory(selectedDate);
      await refreshAllData();
    } catch (err) {
      console.error("Failed to update meal:", err);
      alert("Unable to save meal changes.");
    } finally {
      setSavingEdit(false);
    }
  };

  const mealsList = historyData?.meals || [];
  const totalCal = Math.round(historyData?.total_calories || 0);
  const targetCal = Math.round(historyData?.target_calories || 2000);
  const totalPro = Math.round(historyData?.total_protein || 0);
  const targetPro = Math.round(historyData?.target_protein || 120);
  const totalCarb = Math.round(historyData?.total_carbs || 0);
  const targetCarb = Math.round(historyData?.target_carbs || 250);
  const totalFat = Math.round(historyData?.total_fat || 0);
  const targetFat = Math.round(historyData?.target_fat || 65);
  const totalFib = Math.round(historyData?.total_fiber || 0);
  const targetFib = Math.round(historyData?.target_fiber || 30);

  const calPct = targetCal > 0 ? Math.min(100, Math.round((totalCal / targetCal) * 100)) : 0;
  const proPct = targetPro > 0 ? Math.min(100, Math.round((totalPro / targetPro) * 100)) : 0;
  const carbPct = targetCarb > 0 ? Math.min(100, Math.round((totalCarb / targetCarb) * 100)) : 0;
  const fatPct = targetFat > 0 ? Math.min(100, Math.round((totalFat / targetFat) * 100)) : 0;
  const fibPct = targetFib > 0 ? Math.min(100, Math.round((totalFib / targetFib) * 100)) : 0;

  return (
    <div className="page-container">
      
      {/* 1. Header & Date Navigation Bar */}
      <div className="wellness-card" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)', marginBottom: '4px' }}>
              <Utensils size={18} />
              <span style={{ fontSize: '0.74rem', fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Day-Wise Nutrition Journal
              </span>
            </div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
              Meal History
            </h1>
          </div>

          {/* Date Selector Controls: [← Previous Day] [Today] [Date Picker] [Next Day →] */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={handlePrevDay}
              className="btn-secondary"
              style={{ padding: '8px 14px', fontSize: '0.84rem' }}
              title="Previous Day (Subtract 1 Day)"
            >
              <ChevronLeft size={16} />
              <span>Previous Day</span>
            </button>

            <button
              type="button"
              onClick={handleToday}
              className={isSelectedToday ? "btn-primary" : "btn-secondary"}
              style={{ padding: '8px 14px', fontSize: '0.84rem' }}
            >
              Today
            </button>

            {/* Date Input */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--bg-subtle)', padding: '4px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-glass)' }}>
              <Calendar size={15} color="var(--primary)" />
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => {
                  if (e.target.value) setSelectedDate(e.target.value);
                }}
                style={{
                  border: 'none',
                  background: 'transparent',
                  color: 'var(--text-primary)',
                  fontSize: '0.88rem',
                  fontWeight: '700',
                  outline: 'none',
                  cursor: 'pointer'
                }}
              />
            </div>

            <button
              type="button"
              onClick={handleNextDay}
              className="btn-secondary"
              style={{ padding: '8px 14px', fontSize: '0.84rem' }}
              title="Next Day (Add 1 Day)"
            >
              <span>Next Day</span>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        {/* Selected Date Subtitle */}
        <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--primary)' }}>
            📅 {formatDate(selectedDate)}
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {isSelectedToday ? "Showing today's logged meals" : `Historical journal for ${selectedDate}`}
          </span>
        </div>
      </div>

      {/* 2. Top Daily Nutrition Summary Card */}
      <div className="wellness-card" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: '0 0 16px 0', color: 'var(--text-primary)' }}>
          Daily Nutrition Summary ({formatDate(selectedDate)})
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
          
          {/* Calories */}
          <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-glass)' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--calorie-orange)', textTransform: 'uppercase' }}>Calories</span>
            <div style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
              {totalCal} <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>/ {targetCal}</span>
            </div>
            <div style={{ height: '5px', background: 'var(--bg-elevated, #FFFFFF)', borderRadius: '4px', overflow: 'hidden', marginTop: '8px' }}>
              <div style={{ height: '100%', width: `${calPct}%`, background: 'var(--calorie-gradient)', borderRadius: '4px' }} />
            </div>
          </div>

          {/* Protein */}
          <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-glass)' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--macro-protein)', textTransform: 'uppercase' }}>Protein</span>
            <div style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
              {totalPro}g <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>/ {targetPro}g</span>
            </div>
            <div style={{ height: '5px', background: 'var(--bg-elevated, #FFFFFF)', borderRadius: '4px', overflow: 'hidden', marginTop: '8px' }}>
              <div style={{ height: '100%', width: `${proPct}%`, background: 'var(--macro-protein-gradient)', borderRadius: '4px' }} />
            </div>
          </div>

          {/* Carbs */}
          <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-glass)' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--macro-carbs)', textTransform: 'uppercase' }}>Carbs</span>
            <div style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
              {totalCarb}g <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>/ {targetCarb}g</span>
            </div>
            <div style={{ height: '5px', background: 'var(--bg-elevated, #FFFFFF)', borderRadius: '4px', overflow: 'hidden', marginTop: '8px' }}>
              <div style={{ height: '100%', width: `${carbPct}%`, background: 'var(--macro-carbs-gradient)', borderRadius: '4px' }} />
            </div>
          </div>

          {/* Fat */}
          <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-glass)' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--macro-fat)', textTransform: 'uppercase' }}>Fat</span>
            <div style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
              {totalFat}g <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>/ {targetFat}g</span>
            </div>
            <div style={{ height: '5px', background: 'var(--bg-elevated, #FFFFFF)', borderRadius: '4px', overflow: 'hidden', marginTop: '8px' }}>
              <div style={{ height: '100%', width: `${fatPct}%`, background: 'var(--macro-fat-gradient)', borderRadius: '4px' }} />
            </div>
          </div>

          {/* Fiber */}
          <div style={{ background: 'var(--bg-subtle)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-glass)' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--macro-fiber)', textTransform: 'uppercase' }}>Fiber</span>
            <div style={{ fontSize: '1.25rem', fontWeight: '800', color: 'var(--text-primary)', marginTop: '2px' }}>
              {totalFib}g <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>/ {targetFib}g</span>
            </div>
            <div style={{ height: '5px', background: 'var(--bg-elevated, #FFFFFF)', borderRadius: '4px', overflow: 'hidden', marginTop: '8px' }}>
              <div style={{ height: '100%', width: `${fibPct}%`, background: 'var(--macro-fiber)', borderRadius: '4px' }} />
            </div>
          </div>

        </div>
      </div>

      {/* 3. Chronological Meal Timeline */}
      <div className="wellness-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
              Meal Timeline
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Meals recorded on {formatDate(selectedDate)}
            </span>
          </div>

          <button
            type="button"
            onClick={() => {
              navigate(`/log-meal?date=${selectedDate}`);
            }}
            className="btn-primary"
            style={{ padding: '7px 14px', fontSize: '0.82rem' }}
          >
            <Plus size={15} /> Log Meal for this date
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '36px 0', color: 'var(--text-secondary)' }}>
            Loading meal records for {selectedDate}...
          </div>
        ) : mealsList.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '36px 20px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-lg)' }}>
            <Utensils size={36} color="var(--text-muted)" style={{ margin: '0 auto 10px auto' }} />
            <h4 style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>
              No meals recorded on {formatDate(selectedDate)}
            </h4>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '4px 0 16px 0' }}>
              Navigate to another day or log meals for this date.
            </p>
            <button
              type="button"
              onClick={() => navigate(`/log-meal?date=${selectedDate}`)}
              className="btn-secondary"
              style={{ padding: '8px 18px', fontSize: '0.84rem' }}
            >
              <Plus size={16} /> Add Meal to {selectedDate}
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {mealsList.map((meal) => {
              const items = meal.items || [];
              const mealCal = Math.round(
                meal.totals?.calories !== undefined ? meal.totals.calories :
                (meal.total_calories !== undefined ? meal.total_calories :
                (meal.calories !== undefined ? meal.calories :
                items.reduce((acc, i) => acc + (Number(i.calories) || 0), 0)))
              );
              const mealPro = Math.round(
                meal.totals?.protein_g !== undefined ? meal.totals.protein_g :
                (meal.total_protein !== undefined ? meal.total_protein :
                (meal.protein !== undefined ? meal.protein :
                items.reduce((acc, i) => acc + (Number(i.protein_g || i.protein) || 0), 0)))
              );
              const mealCarb = Math.round(
                meal.totals?.carbs_g !== undefined ? meal.totals.carbs_g :
                (meal.total_carbs !== undefined ? meal.total_carbs :
                (meal.carbs !== undefined ? meal.carbs :
                items.reduce((acc, i) => acc + (Number(i.carbs_g || i.carbs) || 0), 0)))
              );
              const mealFat = Math.round(
                meal.totals?.fat_g !== undefined ? meal.totals.fat_g :
                (meal.total_fat !== undefined ? meal.total_fat :
                (meal.fat !== undefined ? meal.fat :
                items.reduce((acc, i) => acc + (Number(i.fat_g || i.fat) || 0), 0)))
              );

              const timeDisplay = meal.meal_time || meal.time || meal.logged_time || (meal.occurred_at ? (typeof meal.occurred_at === 'string' ? meal.occurred_at.substring(11, 16) : '') : 'Logged');
              const displayMealType = (meal.meal_type || 'meal').replace(/_/g, ' ');

              const itemsSummary = items.length > 0
                ? items.map(it => {
                    const qty = it.quantity !== undefined && it.quantity !== null ? it.quantity : (it.portion !== undefined && it.portion !== null ? it.portion : 1);
                    const name = it.food_name || it.name || 'Food item';
                    return `${qty}x ${name}`;
                  }).join(' • ')
                : 'Food portions recorded';

              return (
                <div
                  key={meal.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '16px 20px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-subtle)',
                    border: '1px solid var(--border-glass)',
                    flexWrap: 'wrap',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <div style={{
                      width: '42px',
                      height: '42px',
                      borderRadius: '10px',
                      background: 'var(--bg-elevated, #FFFFFF)',
                      border: '1px solid var(--border-glass)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '1.2rem'
                    }}>
                      {meal.meal_type === 'breakfast' ? '🌅' : meal.meal_type === 'lunch' ? '☀️' : meal.meal_type === 'snack' ? '☕' : '🌙'}
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: '700' }}>
                          {timeDisplay}
                        </span>
                        <h4 style={{ fontSize: '1.02rem', fontWeight: '800', color: 'var(--text-primary)', margin: 0, textTransform: 'capitalize' }}>
                          {displayMealType}
                        </h4>
                        <span className="badge badge-emerald" style={{ fontSize: '0.68rem', textTransform: 'capitalize' }}>
                          {displayMealType}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px', fontWeight: '500' }}>
                        {itemsSummary}
                      </div>
                    </div>
                  </div>

                  {/* Calories, Macros & Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '1.1rem', fontWeight: '800', color: 'var(--calorie-orange)' }}>
                        {mealCal} kcal
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: '600' }}>
                        P: {mealPro}g • C: {mealCarb}g • F: {mealFat}g
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <button
                        type="button"
                        onClick={() => handleStartEditMeal(meal)}
                        className="btn-secondary"
                        style={{ padding: '6px', borderRadius: '8px', border: 'none' }}
                        title="Edit meal items"
                      >
                        <Edit2 size={16} color="var(--primary)" />
                      </button>

                      <button
                        type="button"
                        onClick={() => handleDeleteMeal(meal.id)}
                        className="btn-secondary"
                        style={{ padding: '6px', borderRadius: '8px', border: 'none', color: 'var(--error-rose)' }}
                        title="Delete meal"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* 4. Bottom Daily Total Bar */}
        {mealsList.length > 0 && (
          <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <span style={{ fontSize: '0.92rem', fontWeight: '800', color: 'var(--text-primary)' }}>
              Total Daily Nutrition:
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.86rem', fontWeight: '700' }}>
              <span style={{ color: 'var(--calorie-orange)' }}>🔥 {totalCal} kcal</span>
              <span style={{ color: 'var(--macro-protein)' }}>🍗 {totalPro}g Protein</span>
              <span style={{ color: 'var(--macro-carbs)' }}>🌾 {totalCarb}g Carbs</span>
              <span style={{ color: 'var(--macro-fat)' }}>🥑 {totalFat}g Fat</span>
              <span style={{ color: 'var(--macro-fiber)' }}>🥗 {totalFib}g Fiber</span>
            </div>
          </div>
        )}
      </div>

      {/* In-Place Meal Editor Modal */}
      {editingMeal && (
        <div className="modal-overlay" onClick={() => setEditingMeal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px', padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.2rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                Edit Meal ({editingMeal.name || editingMeal.meal_type})
              </h3>
              <button
                type="button"
                onClick={() => setEditingMeal(null)}
                className="btn-secondary"
                style={{ padding: '6px', borderRadius: '50%', border: 'none' }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Meal Type Switcher */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '0.78rem', fontWeight: '700', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                Meal Type
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px' }}>
                {['breakfast', 'lunch', 'snack', 'dinner'].map((mType) => (
                  <button
                    key={mType}
                    type="button"
                    onClick={() => setEditMealType(mType)}
                    className={editMealType === mType ? "btn-primary" : "btn-secondary"}
                    style={{ padding: '6px', fontSize: '0.78rem', textTransform: 'capitalize' }}
                  >
                    {mType}
                  </button>
                ))}
              </div>
            </div>

            {/* Meal Items Qty Editor */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
              <label style={{ fontSize: '0.78rem', fontWeight: '700', color: 'var(--text-secondary)' }}>
                Portions & Items
              </label>
              {editItems.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-subtle)', padding: '10px 14px', borderRadius: 'var(--radius-md)' }}>
                  <div>
                    <div style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                      {item.name}
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                      {item.calories} kcal • {item.protein}g P
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Portion:</span>
                    <input
                      type="number"
                      step="0.5"
                      min="0.5"
                      max="10"
                      value={item.portion}
                      onChange={(e) => handleItemQtyChange(idx, e.target.value)}
                      style={{
                        width: '60px',
                        padding: '4px 8px',
                        borderRadius: '6px',
                        border: '1px solid var(--border-glass)',
                        textAlign: 'center',
                        fontSize: '0.85rem',
                        fontWeight: '700'
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Save Actions */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setEditingMeal(null)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveEditMeal}
                disabled={savingEdit}
                className="btn-primary"
              >
                {savingEdit ? 'Saving...' : 'Save Changes'}
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
