import React, { useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { SmartWarningBanner } from '../components/SmartWarningBanner';
import { GoalProgressCard } from '../components/GoalProgressCard';
import { StreakCard } from '../components/StreakCard';
import { ActivityModal } from '../components/ActivityModal';
import { WaterModal } from '../components/WaterModal';
import { ACTIVITY_TYPES } from '../utils/activityConfig';
import { getToday } from '../utils/dateUtils';
import { SmartNutritionRecommendations } from '../components/SmartNutritionRecommendations';
import {
  Flame, Plus, Activity, Utensils,
  TrendingUp, Award, ChevronRight, Trash2, FileText, Droplets,
  CalendarDays, PlusCircle, ArrowUpRight, Dumbbell, Edit2, CheckCircle2,
  Clock, Heart, Sparkles, AlertCircle, History
} from 'lucide-react';

export const DashboardPage = () => {
  const { user, profile, targets, dailyAnalytics, meals, refreshAllData, setTab, navigate } = useStore();
  const [showActivityModal, setShowActivityModal] = useState(false);
  const [showWaterModal, setShowWaterModal] = useState(false);
  const [editingActivity, setEditingActivity] = useState(null);
  const [todayActivities, setTodayActivities] = useState([]);
  const [loadingActivities, setLoadingActivities] = useState(false);
  const [todayWaterLogs, setTodayWaterLogs] = useState([]);
  const [loadingWater, setLoadingWater] = useState(false);
  const [recentFoods, setRecentFoods] = useState([]);

  const todayStr = getToday();

  useEffect(() => {
    refreshAllData();
    fetchActivities();
    fetchWater();
    fetchRecentFoods();
  }, []);

  const fetchRecentFoods = async () => {
    try {
      const rec = await api.getRecentFoods(6);
      setRecentFoods(rec || []);
    } catch (e) {
      console.warn("Could not fetch recent foods for dashboard:", e);
    }
  };

  const fetchActivities = async () => {
    setLoadingActivities(true);
    try {
      const acts = await api.getTodayActivities();
      setTodayActivities(acts || []);
    } catch (e) {
      console.warn("Could not fetch activities:", e);
    } finally {
      setLoadingActivities(false);
    }
  };

  const fetchWater = async () => {
    setLoadingWater(true);
    try {
      const logs = await api.getWaterLogs(todayStr);
      setTodayWaterLogs(logs || []);
    } catch (e) {
      console.warn("Could not fetch water logs:", e);
    } finally {
      setLoadingWater(false);
    }
  };

  const handleDeleteMeal = async (mealId) => {
    if (!window.confirm("Are you sure you want to remove this meal?")) return;
    try {
      await api.deleteMeal(mealId);
      await refreshAllData();
    } catch (e) {
      console.warn("Failed to delete meal:", e);
    }
  };

  const handleDeleteActivity = async (activityId) => {
    if (!window.confirm("Are you sure you want to delete this activity record?")) return;
    try {
      await api.deleteActivity(activityId);
      await refreshAllData();
      await fetchActivities();
    } catch (e) {
      console.warn("Failed to delete activity:", e);
    }
  };

  const handleQuickAddFood = async (food) => {
    try {
      const mealType = 'lunch';
      await api.createMeal({
        meal_type: mealType,
        date: getToday(),
        source: 'quick_add',
        items: [{
          food_id: food.id || food.food_id,
          food_name: food.name,
          quantity: 1,
          serving_unit: 'serving',
          grams: 100.0,
          calories: food.calories || 0,
          protein_g: food.protein_g || food.protein || 0,
          carbs_g: food.carbs_g || food.carbs || 0,
          fat_g: food.fat_g || food.fat || 0,
          fiber_g: food.fiber_g || food.fiber || 0
        }]
      });
      await refreshAllData();
    } catch (e) {
      console.warn("Failed to quick add food:", e);
    }
  };

  const handleQuickWaterAdd = async (amountMl = 250) => {
    try {
      await api.addWater(amountMl, todayStr);
      await refreshAllData();
    } catch (e) {
      console.warn("Failed to quick log water:", e);
    }
  };

  // Nutrition targets and consumed values
  const consumed = dailyAnalytics?.consumed || {};
  const calTarget = targets?.target_calories || 2000;
  const calConsumed = Math.round(consumed.calories || 0);
  const calBurned = Math.round(consumed.burned_calories || 0);
  const calNet = Math.round(consumed.net_calories || calConsumed);
  const calRemaining = Math.max(0, calTarget - calNet);
  const calPct = Math.min(100, Math.round((calConsumed / calTarget) * 100));

  const proteinTarget = targets?.protein_g || 120;
  const proteinConsumed = Math.round(consumed.protein_g || 0);
  const proteinPct = Math.min(100, Math.round((proteinConsumed / proteinTarget) * 100));

  const carbsTarget = targets?.carbs_g || 250;
  const carbsConsumed = Math.round(consumed.carbs_g || 0);
  const carbsPct = Math.min(100, Math.round((carbsConsumed / carbsTarget) * 100));

  const fatTarget = targets?.fat_g || 65;
  const fatConsumed = Math.round(consumed.fat_g || 0);
  const fatPct = Math.min(100, Math.round((fatConsumed / fatTarget) * 100));

  const fiberTarget = targets?.fiber_g || 30;
  const fiberConsumed = Math.round(consumed.fiber_g || 0);
  const fiberPct = Math.min(100, Math.round((fiberConsumed / fiberTarget) * 100));

  const formatLiters = (ml) => {
    if (!ml || isNaN(ml) || ml <= 0) return '0.0';
    const l = ml / 1000;
    if (Number.isInteger(l)) return `${l.toFixed(1)}`;
    const fixed = l.toFixed(2);
    return fixed.endsWith('0') ? l.toFixed(1) : fixed;
  };

  const waterTargetL = formatLiters(targets?.water_ml || 2500);
  const waterConsumedL = formatLiters(consumed.water_ml || 0);
  const waterPct = Math.min(100, Math.round(((consumed.water_ml || 0) / (targets?.water_ml || 2500)) * 100));

  // Determine time of day greeting
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const firstName = profile?.name ? profile.name.split(' ')[0] : 'there';

  const formattedToday = new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  }).format(new Date());

  // Meal types definition for timeline
  const mealSlots = [
    { type: 'breakfast', label: 'Breakfast', defaultTime: '08:00', icon: '🌅' },
    { type: 'lunch', label: 'Lunch', defaultTime: '13:00', icon: '☀️' },
    { type: 'snack', label: 'Snack', defaultTime: '17:00', icon: '☕' },
    { type: 'dinner', label: 'Dinner', defaultTime: '20:00', icon: '🌙' }
  ];

  const todayMeals = meals || [];

  return (
    <div className="page-container">
      
      {/* 1. Header with Personalized Greeting & Date */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '1.85rem', fontWeight: '800', color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.02em' }}>
            {greeting}, {firstName}
          </h1>
          <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
            Here's your nutrition snapshot for today.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            className="wellness-card"
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-full)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.84rem',
              fontWeight: '700',
              color: 'var(--text-primary)'
            }}
          >
            <CalendarDays size={16} color="var(--primary)" />
            <span>{formattedToday}</span>
          </div>

          <button
            type="button"
            onClick={() => setTab('add_food')}
            className="btn-primary"
            style={{ padding: '8px 16px', fontSize: '0.84rem' }}
          >
            <Plus size={16} /> Log Meal
          </button>
        </div>
      </div>

      {/* Smart Warning Banner (if any deficit/excess alert exists) */}
      <SmartWarningBanner />

      {/* 2. Hero Section: Today's Progress */}
      <div className="wellness-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
              Today's Progress
            </h2>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Calorie budget & macronutrient balance
            </span>
          </div>
          <span className="badge badge-emerald" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
            {calRemaining} kcal remaining
          </span>
        </div>

        {/* Calories & Macro Breakdown Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
          
          {/* Main Calorie Gauge Card */}
          <div style={{ background: 'var(--bg-subtle)', padding: '20px', borderRadius: 'var(--radius-lg)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'var(--calorie-orange-light)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Flame size={18} color="var(--calorie-orange)" />
                </div>
                <div>
                  <span style={{ fontSize: '0.72rem', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Energy Budget</span>
                  <div style={{ fontSize: '1.35rem', fontWeight: '800', color: 'var(--text-primary)' }}>
                    {calConsumed.toLocaleString()} <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: '600' }}>/ {calTarget.toLocaleString()} kcal</span>
                  </div>
                </div>
              </div>
              <span className="badge" style={{ background: 'var(--bg-elevated, #FFFFFF)', color: 'var(--calorie-orange)', border: '1px solid rgba(231, 111, 81, 0.25)', fontSize: '0.8rem', fontWeight: '800' }}>
                {calPct}%
              </span>
            </div>

            {/* Calorie Progress Bar */}
            <div>
              <div style={{ height: '10px', background: 'var(--bg-elevated, #FFFFFF)', borderRadius: '9999px', overflow: 'hidden', border: '1px solid var(--border-glass)' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${calPct}%`,
                    background: 'var(--calorie-gradient)',
                    borderRadius: '9999px',
                    transition: 'width 0.4s ease'
                  }}
                />
              </div>
            </div>

            {/* Calorie Stats Breakdown */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', paddingTop: '8px', borderTop: '1px solid var(--border-glass)' }}>
              <div>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Burned</span>
                <div style={{ fontSize: '0.92rem', fontWeight: '800', color: 'var(--primary)' }}>
                  {calBurned} kcal
                </div>
              </div>
              <div>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Net</span>
                <div style={{ fontSize: '0.92rem', fontWeight: '800', color: 'var(--text-primary)' }}>
                  {calNet} kcal
                </div>
              </div>
              <div>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Remaining</span>
                <div style={{ fontSize: '0.92rem', fontWeight: '800', color: 'var(--primary)' }}>
                  {calRemaining} kcal
                </div>
              </div>
            </div>
          </div>

          {/* Macronutrients & Water Progress Bars */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', justifyContent: 'center' }}>
            
            {/* Protein */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '4px' }}>
                <span style={{ fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--macro-protein)' }} /> Protein
                </span>
                <span style={{ color: 'var(--text-secondary)', fontWeight: '600' }}>
                  {proteinConsumed} / {proteinTarget} g <strong style={{ color: 'var(--macro-protein)', marginLeft: '4px' }}>({proteinPct}%)</strong>
                </span>
              </div>
              <div style={{ height: '7px', background: 'var(--bg-subtle)', borderRadius: '9999px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${proteinPct}%`, background: 'var(--macro-protein-gradient)', borderRadius: '9999px', transition: 'width 0.3s ease' }} />
              </div>
            </div>

            {/* Carbohydrates */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '4px' }}>
                <span style={{ fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--macro-carbs)' }} /> Carbohydrates
                </span>
                <span style={{ color: 'var(--text-secondary)', fontWeight: '600' }}>
                  {carbsConsumed} / {carbsTarget} g <strong style={{ color: 'var(--macro-carbs)', marginLeft: '4px' }}>({carbsPct}%)</strong>
                </span>
              </div>
              <div style={{ height: '7px', background: 'var(--bg-subtle)', borderRadius: '9999px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${carbsPct}%`, background: 'var(--macro-carbs-gradient)', borderRadius: '9999px', transition: 'width 0.3s ease' }} />
              </div>
            </div>

            {/* Fat */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '4px' }}>
                <span style={{ fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--macro-fat)' }} /> Healthy Fat
                </span>
                <span style={{ color: 'var(--text-secondary)', fontWeight: '600' }}>
                  {fatConsumed} / {fatTarget} g <strong style={{ color: 'var(--macro-fat)', marginLeft: '4px' }}>({fatPct}%)</strong>
                </span>
              </div>
              <div style={{ height: '7px', background: 'var(--bg-subtle)', borderRadius: '9999px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${fatPct}%`, background: 'var(--macro-fat-gradient)', borderRadius: '9999px', transition: 'width 0.3s ease' }} />
              </div>
            </div>

            {/* Fiber */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '4px' }}>
                <span style={{ fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--macro-fiber)' }} /> Dietary Fiber
                </span>
                <span style={{ color: 'var(--text-secondary)', fontWeight: '600' }}>
                  {fiberConsumed} / {fiberTarget} g <strong style={{ color: 'var(--macro-fiber)', marginLeft: '4px' }}>({fiberPct}%)</strong>
                </span>
              </div>
              <div style={{ height: '7px', background: 'var(--bg-subtle)', borderRadius: '9999px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${fiberPct}%`, background: 'var(--macro-fiber)', borderRadius: '9999px', transition: 'width 0.3s ease' }} />
              </div>
            </div>

            {/* Water */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '4px' }}>
                <span style={{ fontWeight: '700', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--hydration-cyan)' }} /> Water Intake
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ color: 'var(--text-secondary)', fontWeight: '600' }}>
                    {waterConsumedL} / {waterTargetL} L <strong style={{ color: 'var(--hydration-cyan)', marginLeft: '2px' }}>({waterPct}%)</strong>
                  </span>
                  <button
                    type="button"
                    onClick={() => handleQuickWaterAdd(250)}
                    style={{ background: 'var(--hydration-cyan-light)', color: 'var(--hydration-cyan)', border: 'none', borderRadius: '4px', padding: '1px 5px', fontSize: '0.7rem', fontWeight: '800', cursor: 'pointer' }}
                  >
                    +250ml
                  </button>
                </div>
              </div>
              <div style={{ height: '7px', background: 'var(--bg-subtle)', borderRadius: '9999px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${waterPct}%`, background: 'var(--hydration-gradient)', borderRadius: '9999px', transition: 'width 0.3s ease' }} />
              </div>
            </div>

          </div>
        </div>
      </div>

      {/* 3. 2-Column Grid: Goal Progress & Streak System */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        <GoalProgressCard onGoalUpdated={refreshAllData} />
        <StreakCard onLogClick={() => setTab('add_food')} />
      </div>

      {/* 4. Smart Nutrition Food Recommendations */}
      <SmartNutritionRecommendations targetDate={todayStr} />

      {/* 5. Today's Meals Timeline */}
      <div className="wellness-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
              Today's Meals
            </h2>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Chronological nutrition logs for today
            </span>
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => navigate('/meal-history')}
              className="btn-secondary"
              style={{ padding: '6px 12px', fontSize: '0.82rem', gap: '5px' }}
            >
              <History size={14} /> History
            </button>
            <button
              type="button"
              onClick={() => navigate('/log-meal')}
              className="btn-primary"
              style={{ padding: '6px 14px', fontSize: '0.82rem', gap: '5px' }}
            >
              <Plus size={15} /> Add Meal
            </button>
          </div>
        </div>

        {todayMeals.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '36px 20px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-lg)' }}>
            <Utensils size={36} color="var(--text-muted)" style={{ margin: '0 auto 10px auto' }} />
            <h4 style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>
              Your nutrition journal is empty for today
            </h4>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: '4px 0 16px 0' }}>
              Log your breakfast, lunch, snacks or dinner to start tracking your macros.
            </p>
            <button
              type="button"
              onClick={() => setTab('add_food')}
              className="btn-primary"
              style={{ padding: '8px 18px', fontSize: '0.84rem' }}
            >
              <Plus size={16} /> Log your first meal
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {todayMeals.map((meal) => {
              const itemsList = meal.items || [];
              const mealCalories = Math.round(
                meal.totals?.calories !== undefined ? meal.totals.calories :
                (meal.total_calories !== undefined ? meal.total_calories :
                (meal.calories !== undefined ? meal.calories :
                itemsList.reduce((acc, i) => acc + (Number(i.calories) || 0), 0)))
              );
              const mealProtein = Math.round(
                meal.totals?.protein_g !== undefined ? meal.totals.protein_g :
                (meal.total_protein !== undefined ? meal.total_protein :
                (meal.protein !== undefined ? meal.protein :
                itemsList.reduce((acc, i) => acc + (Number(i.protein_g || i.protein) || 0), 0)))
              );
              const mealCarbs = Math.round(
                meal.totals?.carbs_g !== undefined ? meal.totals.carbs_g :
                (meal.total_carbs !== undefined ? meal.total_carbs :
                (meal.carbs !== undefined ? meal.carbs :
                itemsList.reduce((acc, i) => acc + (Number(i.carbs_g || i.carbs) || 0), 0)))
              );
              const mealFat = Math.round(
                meal.totals?.fat_g !== undefined ? meal.totals.fat_g :
                (meal.total_fat !== undefined ? meal.total_fat :
                (meal.fat !== undefined ? meal.fat :
                itemsList.reduce((acc, i) => acc + (Number(i.fat_g || i.fat) || 0), 0)))
              );

              const timeDisplay = meal.meal_time || meal.time || meal.logged_time || (meal.occurred_at ? (typeof meal.occurred_at === 'string' ? meal.occurred_at.substring(11, 16) : '') : 'Logged');
              const displayMealType = (meal.meal_type || 'meal').replace(/_/g, ' ');

              const itemsSummary = itemsList.length > 0
                ? itemsList.map(it => {
                    const qty = it.quantity !== undefined && it.quantity !== null ? it.quantity : (it.portion !== undefined && it.portion !== null ? it.portion : 1);
                    const name = it.food_name || it.name || 'Food item';
                    return `${qty}x ${name}`;
                  }).join(', ')
                : 'Portion recorded';

              return (
                <div
                  key={meal.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '14px 18px',
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
                        <h4 style={{ fontSize: '0.98rem', fontWeight: '800', color: 'var(--text-primary)', margin: 0, textTransform: 'capitalize' }}>
                          {displayMealType}
                        </h4>
                        <span className="badge badge-emerald" style={{ fontSize: '0.68rem', textTransform: 'capitalize' }}>
                          {displayMealType}
                        </span>
                        <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                          • {timeDisplay}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px', fontWeight: '500' }}>
                        {itemsSummary}
                      </div>
                    </div>
                  </div>

                  {/* Calories, Macros & Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '1.05rem', fontWeight: '800', color: 'var(--calorie-orange)' }}>
                        {mealCalories} kcal
                      </div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', fontWeight: '600' }}>
                        P: {mealProtein}g • C: {mealCarbs}g • F: {mealFat}g
                      </div>
                    </div>

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
              );
            })}
          </div>
        )}
      </div>

      {/* 5. Recently Tracked Foods (Quick Shortcuts) */}
      {recentFoods.length > 0 && (
        <div className="wellness-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                Recently Tracked Foods
              </h3>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                1-Click shortcut to log frequent meals
              </span>
            </div>
            <button
              type="button"
              onClick={() => setTab('search')}
              className="btn-secondary"
              style={{ padding: '4px 12px', fontSize: '0.78rem' }}
            >
              Browse Catalog
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
            {recentFoods.slice(0, 6).map((food, idx) => (
              <div
                key={idx}
                onClick={() => handleQuickAddFood(food)}
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border-glass)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '8px',
                  transition: 'all 0.18s ease'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'var(--primary)';
                  e.currentTarget.style.background = 'var(--primary-light)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'var(--border-glass)';
                  e.currentTarget.style.background = 'var(--bg-subtle)';
                }}
              >
                <div>
                  <div style={{ fontSize: '0.88rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                    {food.name}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                    {food.calories} kcal • {food.protein}g protein
                  </div>
                </div>
                <div style={{ width: '26px', height: '26px', borderRadius: '50%', background: 'var(--bg-elevated, #FFFFFF)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}>
                  <Plus size={15} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. Physical Activity Log */}
      <div className="wellness-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
              Physical Activity & Workouts
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Track calories burned and step counts
            </span>
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => navigate('/activity-history')}
              className="btn-secondary"
              style={{ padding: '6px 12px', fontSize: '0.82rem', gap: '5px' }}
            >
              <History size={14} /> History
            </button>
            <button
              type="button"
              onClick={() => { setEditingActivity(null); setShowActivityModal(true); }}
              className="btn-primary"
              style={{ padding: '6px 14px', fontSize: '0.82rem', gap: '5px' }}
            >
              <Plus size={15} /> Log Activity
            </button>
          </div>
        </div>

        {todayActivities.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '24px', background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)' }}>
            <Dumbbell size={28} color="var(--text-muted)" style={{ margin: '0 auto 8px auto' }} />
            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', margin: 0 }}>
              No workouts logged for today.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {todayActivities.map((act) => (
              <div
                key={act.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border-glass)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: 'var(--bg-elevated, #FFFFFF)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}>
                    <Activity size={18} />
                  </div>
                  <div>
                    <div style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                      {act.activity_name || act.activity_type}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {act.duration_minutes} min • {act.intensity || 'moderate'} intensity
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <span style={{ fontSize: '0.98rem', fontWeight: '800', color: 'var(--primary)' }}>
                    -{Math.round(act.calories_burned || 0)} kcal
                  </span>
                  <button
                    type="button"
                    onClick={() => handleDeleteActivity(act.id)}
                    className="btn-secondary"
                    style={{ padding: '5px', borderRadius: '6px', border: 'none', color: 'var(--error-rose)' }}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      {showActivityModal && (
        <ActivityModal
          isOpen={showActivityModal}
          onClose={() => { setShowActivityModal(false); setEditingActivity(null); }}
          onActivitySaved={() => { fetchActivities(); refreshAllData(); }}
          initialData={editingActivity}
        />
      )}

      {showWaterModal && (
        <WaterModal
          isOpen={showWaterModal}
          onClose={() => setShowWaterModal(false)}
          onWaterLogged={() => { fetchWater(); refreshAllData(); }}
        />
      )}

    </div>
  );
};
