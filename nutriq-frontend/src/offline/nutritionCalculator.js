/**
 * NutriQ Offline Nutrition Engine
 * Single source of truth for offline macro calculations, daily summary aggregation,
 * and weekly summary computation when backend is unavailable.
 */
import { calculateCalorieStatus } from '../utils/calorieStatus.js';
import { getLocalDate, getToday } from '../utils/dateUtils.js';

export const calculatePortionNutrition = (food, quantity = 1.0, servingUnit = 'serving') => {
  if (!food) return { calories: 0, protein_g: 0, carbs_g: 0, fat_g: 0, fiber_g: 0, grams: 100 };

  const qty = Math.max(0, parseFloat(quantity) || 1.0);
  const baseGrams = parseFloat(food.serving_grams || food.serving_size_g || 100.0) || 100.0;
  const totalGrams = baseGrams * qty;

  // Factor relative to 100g base if food is per 100g, or direct unit scaling
  const baseCal = parseFloat(food.calories || 0.0);
  const basePro = parseFloat(food.protein_g || food.protein || 0.0);
  const baseCarb = parseFloat(food.carbs_g || food.carbohydrates || 0.0);
  const baseFat = parseFloat(food.fat_g || food.fat || 0.0);
  const baseFib = parseFloat(food.fiber_g || food.fiber || 0.0);

  return {
    grams: Math.round(totalGrams * 10) / 10,
    calories: Math.round(baseCal * qty * 10) / 10,
    protein_g: Math.round(basePro * qty * 10) / 10,
    carbs_g: Math.round(baseCarb * qty * 10) / 10,
    fat_g: Math.round(baseFat * qty * 10) / 10,
    fiber_g: Math.round(baseFib * qty * 10) / 10,
  };
};

export const calculateLocalDailySummary = (allMeals = [], waterLogs = [], profile = null, targets = null, dateStr = null, exerciseLogs = []) => {
  const targetDateStr = dateStr || getToday();

  const calTarget = parseFloat(targets?.target_calories || profile?.calorie_target || 2000.0);
  const proTarget = parseFloat(targets?.protein_g || profile?.protein_target_g || 100.0);
  const carbTarget = parseFloat(targets?.carbs_g || 250.0);
  const fatTarget = parseFloat(targets?.fat_g || 60.0);
  const fibTarget = parseFloat(targets?.fiber_g || 28.0);
  const waterTarget = parseFloat(targets?.water_ml || 2500.0);

  // Filter meals for this date (YYYY-MM-DD) using timezone-safe getLocalDate
  const dayMeals = allMeals.filter(m => {
    if (!m) return false;
    const mDate = getLocalDate(m.occurred_at || m.date);
    return mDate === targetDateStr;
  });

  const slots = {
    breakfast: { logged: false, meal_count: 0, total_calories: 0.0, total_protein_g: 0.0, total_carbs_g: 0.0, total_fat_g: 0.0, total_fiber_g: 0.0, items: [] },
    lunch: { logged: false, meal_count: 0, total_calories: 0.0, total_protein_g: 0.0, total_carbs_g: 0.0, total_fat_g: 0.0, total_fiber_g: 0.0, items: [] },
    snack: { logged: false, meal_count: 0, total_calories: 0.0, total_protein_g: 0.0, total_carbs_g: 0.0, total_fat_g: 0.0, total_fiber_g: 0.0, items: [] },
    dinner: { logged: false, meal_count: 0, total_calories: 0.0, total_protein_g: 0.0, total_carbs_g: 0.0, total_fat_g: 0.0, total_fiber_g: 0.0, items: [] }
  };

  let totalConsumedCal = 0.0;
  let totalConsumedPro = 0.0;
  let totalConsumedCarb = 0.0;
  let totalConsumedFat = 0.0;
  let totalConsumedFib = 0.0;

  dayMeals.forEach(m => {
    const rawType = (m.meal_type || 'snack').toLowerCase();
    let slotKey = 'snack';
    if (rawType.includes('breakfast') || rawType.includes('morning')) slotKey = 'breakfast';
    else if (rawType.includes('lunch') || rawType.includes('afternoon')) slotKey = 'lunch';
    else if (rawType.includes('dinner') || rawType.includes('night') || rawType.includes('supper')) slotKey = 'dinner';
    else slotKey = 'snack';

    slots[slotKey].logged = true;
    slots[slotKey].meal_count += 1;

    const items = Array.isArray(m.items) ? m.items : [];
    items.forEach(itm => {
      const cal = parseFloat(itm.calories || 0.0);
      const pro = parseFloat(itm.protein_g || itm.protein || 0.0);
      const carb = parseFloat(itm.carbs_g || itm.carbohydrates || 0.0);
      const fat = parseFloat(itm.fat_g || itm.fat || 0.0);
      const fib = parseFloat(itm.fiber_g || itm.fiber || 0.0);
      const foodName = itm.food_name || itm.name || itm.title || "Food Item";
      const quantity = parseFloat(itm.quantity || itm.amount || 1.0);
      const unit = itm.serving_unit || itm.unit || "serving";

      slots[slotKey].total_calories += cal;
      slots[slotKey].total_protein_g += pro;
      slots[slotKey].total_carbs_g += carb;
      slots[slotKey].total_fat_g += fat;
      slots[slotKey].total_fiber_g += fib;
      slots[slotKey].items.push({
        ...itm,
        food_name: foodName,
        quantity: quantity,
        serving_unit: unit,
        calories: Math.round(cal * 10) / 10,
        protein_g: Math.round(pro * 10) / 10,
        carbs_g: Math.round(carb * 10) / 10,
        fat_g: Math.round(fat * 10) / 10,
        fiber_g: Math.round(fib * 10) / 10
      });

      totalConsumedCal += cal;
      totalConsumedPro += pro;
      totalConsumedCarb += carb;
      totalConsumedFat += fat;
      totalConsumedFib += fib;
    });
  });

  // Hydration for this date
  const dayWaterLogs = waterLogs.filter(w => {
    if (!w) return false;
    const wDate = getLocalDate(w.recorded_at || w.date);
    return wDate === targetDateStr;
  });
  const totalWater = dayWaterLogs.reduce((acc, w) => acc + (parseFloat(w.amount_ml || 0.0)), 0.0);

  // Exercise for this date
  const dayExerciseLogs = (exerciseLogs || []).filter(e => {
    if (!e) return false;
    const eDate = getLocalDate(e.recorded_at || e.date);
    return eDate === targetDateStr;
  });

  const totalBurned = dayExerciseLogs.reduce((acc, e) => acc + (parseFloat(e.calories_burned_est || e.calories_burned || 0.0)), 0.0);
  const totalDuration = dayExerciseLogs.reduce((acc, e) => acc + (parseInt(e.duration_min || e.duration_minutes || 0)), 0);
  const activities = dayExerciseLogs.map(e => {
    const raw = e.type || e.activity_type || 'Workout';
    return raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  });

  const exerciseItems = dayExerciseLogs.map(e => {
    const rawType = e.type || e.activity_type || 'walking';
    const actName = rawType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const dt = e.recorded_at ? new Date(e.recorded_at) : new Date();
    const timeStr = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return {
      id: e.id || 'ex_' + Math.random(),
      type: rawType,
      activity_name: actName,
      duration_min: parseInt(e.duration_min || e.duration_minutes || 0),
      intensity: e.intensity || 'moderate',
      calories_burned: Math.round(parseFloat(e.calories_burned_est || e.calories_burned || 0.0) * 10) / 10,
      time: timeStr,
      recorded_at: e.recorded_at || new Date().toISOString()
    };
  });

  const loggedSlotsCount = Object.values(slots).filter(s => s.logged).length;
  const remainingCal = Math.max(0, Math.round((calTarget - totalConsumedCal) * 10) / 10);
  const remainingPro = Math.max(0, Math.round((proTarget - totalConsumedPro) * 10) / 10);
  const remainingCarb = Math.max(0, Math.round((carbTarget - totalConsumedCarb) * 10) / 10);
  const remainingFat = Math.max(0, Math.round((fatTarget - totalConsumedFat) * 10) / 10);
  const remainingFib = Math.max(0, Math.round((fibTarget - totalConsumedFib) * 10) / 10);
  const remainingWaterMl = Math.max(0, Math.round(waterTarget - totalWater));
  const remainingWaterL = Math.max(0, Math.round((remainingWaterMl / 1000.0) * 10) / 10);
  const isOver = totalConsumedCal > calTarget;
  const overAmount = isOver ? (totalConsumedCal - calTarget) : 0.0;
  const netCal = Math.round((totalConsumedCal - totalBurned) * 10) / 10;

  return {
    date: targetDateStr,
    display_date: new Date(targetDateStr + 'T00:00:00').toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' }),
    is_today: targetDateStr === getToday(),
    is_offline: true,
    has_data: totalConsumedCal > 0 || totalWater > 0 || dayMeals.length > 0 || dayExerciseLogs.length > 0,
    calories: {
      target: calTarget,
      consumed: Math.round(totalConsumedCal * 10) / 10,
      remaining: remainingCal,
      burned: Math.round(totalBurned * 10) / 10,
      net: netCal,
      is_over: isOver,
      over_amount: Math.round(overAmount * 10) / 10
    },
    macros: {
      protein: {
        target: proTarget,
        consumed: Math.round(totalConsumedPro * 10) / 10,
        remaining: remainingPro,
        percentage: Math.min(100, Math.round((totalConsumedPro / proTarget) * 100))
      },
      carbohydrates: {
        target: carbTarget,
        consumed: Math.round(totalConsumedCarb * 10) / 10,
        remaining: remainingCarb,
        percentage: Math.min(100, Math.round((totalConsumedCarb / carbTarget) * 100)),
        is_exceeded: totalConsumedCarb >= carbTarget
      },
      fat: {
        target: fatTarget,
        consumed: Math.round(totalConsumedFat * 10) / 10,
        remaining: remainingFat,
        percentage: Math.min(100, Math.round((totalConsumedFat / fatTarget) * 100))
      },
      fiber: {
        target: fibTarget,
        consumed: Math.round(totalConsumedFib * 10) / 10,
        remaining: remainingFib,
        percentage: Math.min(100, Math.round((totalConsumedFib / fibTarget) * 100))
      }
    },
    hydration: {
      target_ml: waterTarget,
      consumed_ml: Math.round(totalWater),
      remaining_ml: remainingWaterMl,
      remaining_l: remainingWaterL,
      percentage: Math.min(100, Math.round((totalWater / waterTarget) * 100)),
      is_zero: totalWater === 0
    },
    meals: {
      breakfast: slots.breakfast,
      lunch: slots.lunch,
      snack: slots.snack,
      dinner: slots.dinner,
      logged_count: loggedSlotsCount,
      total_slots: 4
    },
    exercise: {
      logged: dayExerciseLogs.length > 0,
      duration_minutes: totalDuration,
      calories_burned: Math.round(totalBurned * 10) / 10,
      activities: activities,
      items: exerciseItems,
      message: dayExerciseLogs.length > 0 ? `${totalDuration} mins, ${Math.round(totalBurned)} kcal burned` : "No exercise logged today."
    },
    goal: profile?.fitness_goal || 'maintain',
    goal_display: (profile?.fitness_goal || 'Maintain').replace('_', ' '),
    ...(() => {
      const calStatus = calculateCalorieStatus({
        targetCalories: calTarget,
        consumedCalories: totalConsumedCal,
        burnedCalories: totalBurned,
        goalType: profile?.fitness_goal || 'maintain',
        hasMeals: totalConsumedCal > 0
      });
      return {
        goal_status: calStatus.statusBadge,
        status_level: calStatus.statusLevel,
        status_badge: calStatus.statusBadge,
        calorie_status: calStatus,
        daily_insight: calStatus.message,
        calorie_warning: calStatus.warningMessage
      };
    })(),
    progress_score: Math.min(100, Math.round((totalConsumedCal / calTarget) * 100)),
    progress_score_explanation: "Calculated from local offline meal logs."
  };
};

export const calculateLocalWeeklySummary = (allMeals = [], waterLogs = [], profile = null, targets = null, weekStartStr = null, exerciseLogs = []) => {
  const now = new Date();
  const todayStr = new Date().toISOString().split('T')[0];
  let startDate;

  if (weekStartStr) {
    startDate = new Date(weekStartStr + 'T00:00:00');
  } else {
    // Current week Monday
    startDate = new Date(now);
    const day = startDate.getDay();
    const diff = startDate.getDate() - day + (day === 0 ? -6 : 1);
    startDate.setDate(diff);
  }

  const dayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const dailyBreakdown = [];

  let totalCal = 0.0;
  let totalPro = 0.0;
  let totalCarb = 0.0;
  let totalFat = 0.0;
  let totalFib = 0.0;
  let totalWater = 0.0;
  let totalBurned = 0.0;
  let totalActiveMins = 0;
  let activeDaysCount = 0;
  let totalMeals = 0;
  let daysComplete = 0;
  let daysLogged = 0;
  let adherentDays = 0;
  let daysOverCal = 0;
  let bestWaterDay = null;
  let maxWaterMl = 0.0;
  let elapsedDays = 0;

  const calTarget = parseFloat(targets?.target_calories || profile?.calorie_target || 2000.0);
  const proTarget = parseFloat(targets?.protein_g || profile?.protein_target_g || 100.0);
  const waterTarget = parseFloat(targets?.water_ml || 2500.0);

  for (let i = 0; i < 7; i++) {
    const curDate = new Date(startDate);
    curDate.setDate(startDate.getDate() + i);
    const curDateStr = curDate.toISOString().split('T')[0];
    const dayName = dayNames[i];
    const isToday = (curDateStr === todayStr);
    const isFuture = (curDateStr > todayStr);

    if (!isFuture) {
      elapsedDays += 1;
    }

    const daySummary = isFuture
      ? {
          calories: { consumed: 0, target: calTarget, remaining: calTarget, burned: 0, net: 0 },
          macros: { protein: { target: proTarget, consumed: 0 }, carbohydrates: { target: 250, consumed: 0 }, fat: { target: 60, consumed: 0 }, fiber: { target: 28, consumed: 0 } },
          hydration: { target_ml: waterTarget, consumed_ml: 0, remaining_ml: waterTarget },
          meals: { breakfast: { logged: false }, lunch: { logged: false }, snack: { logged: false }, dinner: { logged: false }, logged_count: 0 },
          exercise: { logged: false, duration_minutes: 0, calories_burned: 0, activities: [] }
        }
      : calculateLocalDailySummary(allMeals, waterLogs, profile, targets, curDateStr, exerciseLogs);

    const calConsumed = daySummary.calories.consumed || 0;
    const proConsumed = daySummary.macros.protein.consumed || 0;
    const carbConsumed = daySummary.macros.carbohydrates.consumed || 0;
    const fatConsumed = daySummary.macros.fat.consumed || 0;
    const fibConsumed = daySummary.macros.fiber.consumed || 0;
    const waterConsumed = daySummary.hydration.consumed_ml || 0;
    const loggedCount = daySummary.meals.logged_count || 0;
    const burnedCal = daySummary.exercise.calories_burned || 0;
    const activeMins = daySummary.exercise.duration_minutes || 0;
    const activities = daySummary.exercise.activities || [];

    const bLogged = Boolean(daySummary.meals.breakfast?.logged);
    const lLogged = Boolean(daySummary.meals.lunch?.logged);
    const sLogged = Boolean(daySummary.meals.snack?.logged);
    const dLogged = Boolean(daySummary.meals.dinner?.logged);

    const hasData = (loggedCount > 0 || calConsumed > 0 || burnedCal > 0 || waterConsumed > 0) && !isFuture;
    const isComplete = (loggedCount >= 3 || (bLogged && lLogged && dLogged)) && !isFuture;

    if (isComplete) daysComplete += 1;
    if (hasData) daysLogged += 1;

    if (!isFuture && (burnedCal > 0 || activeMins > 0)) {
      activeDaysCount += 1;
    }

    if (!isFuture && calConsumed > 0) {
      if (Math.abs(calConsumed - calTarget) <= (calTarget * 0.15)) {
        adherentDays += 1;
      }
      if (calConsumed > calTarget + 50) {
        daysOverCal += 1;
      }
    }

    if (!isFuture && waterConsumed > maxWaterMl) {
      maxWaterMl = waterConsumed;
      bestWaterDay = dayName;
    }

    if (!isFuture) {
      totalCal += calConsumed;
      totalPro += proConsumed;
      totalCarb += carbConsumed;
      totalFat += fatConsumed;
      totalFib += fibConsumed;
      totalWater += waterConsumed;
      totalBurned += burnedCal;
      totalActiveMins += activeMins;
      totalMeals += loggedCount;
    }

    dailyBreakdown.push({
      day_name: dayName,
      date: curDateStr,
      calories_consumed: calConsumed,
      calorie_target: calTarget,
      exercise_burned_kcal: burnedCal,
      active_minutes: activeMins,
      activities: activities,
      protein_consumed_g: proConsumed,
      protein_target_g: proTarget,
      carbs_consumed_g: carbConsumed,
      fat_consumed_g: fatConsumed,
      fiber_consumed_g: fibConsumed,
      water_consumed_ml: waterConsumed,
      water_target_ml: waterTarget,
      meals_logged_count: loggedCount,
      is_complete: isComplete,
      breakfast_logged: bLogged,
      lunch_logged: lLogged,
      snack_logged: sLogged,
      dinner_logged: dLogged,
      is_today: isToday,
      is_future: isFuture,
      has_data: hasData,
      calories: calConsumed,
      protein_g: proConsumed,
      carbs_g: carbConsumed,
      fat_g: fatConsumed,
      fiber_g: fibConsumed,
      water_ml: waterConsumed
    });
  }

  const divisor = elapsedDays > 0 ? elapsedDays : 7.0;
  const avgCal = elapsedDays > 0 ? Math.round((totalCal / divisor) * 10) / 10 : 0.0;
  const avgPro = elapsedDays > 0 ? Math.round((totalPro / divisor) * 10) / 10 : 0.0;
  const avgCarb = elapsedDays > 0 ? Math.round((totalCarb / divisor) * 10) / 10 : 0.0;
  const avgFat = elapsedDays > 0 ? Math.round((totalFat / divisor) * 10) / 10 : 0.0;
  const avgFib = elapsedDays > 0 ? Math.round((totalFib / divisor) * 10) / 10 : 0.0;
  const avgWater = elapsedDays > 0 ? Math.round((totalWater / divisor) * 10) / 10 : 0.0;
  const avgBurned = elapsedDays > 0 ? Math.round((totalBurned / divisor) * 10) / 10 : 0.0;

  const daysMissed = Math.max(0, elapsedDays - daysLogged);
  const adherencePct = (elapsedDays > 0 && daysLogged > 0) ? Math.round((adherentDays / divisor) * 1000) / 10 : 0.0;
  const hasData = totalCal > 0 || totalWater > 0 || totalMeals > 0 || totalBurned > 0;
  const avgLabel = elapsedDays < 7 && elapsedDays > 0 ? `${elapsedDays}-Day Average` : "7-Day Average";

  const endDate = new Date(startDate);
  endDate.setDate(startDate.getDate() + 6);
  const startStr = startDate.toISOString().split('T')[0];
  const endStr = endDate.toISOString().split('T')[0];
  const displayRange = `${startDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${endDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`;

  const insights = [];
  if (!hasData) {
    insights.push("Not enough data to generate a weekly summary. Start logging meals or activity offline or online to view trends.");
  } else {
    if (Math.abs(avgCal - calTarget) <= (calTarget * 0.1)) {
      insights.push(`Your average calorie intake (${avgCal} kcal) was close to your daily target (${calTarget} kcal) this week.`);
    } else if (avgCal > calTarget) {
      insights.push(`Your average calorie intake (${avgCal} kcal) was above your daily target by ${Math.round(avgCal - calTarget)} kcal.`);
    } else {
      insights.push(`Your average calorie intake (${avgCal} kcal) was ${Math.round(calTarget - avgCal)} kcal below your daily target.`);
    }

    insights.push(`You logged activity and meals on ${daysLogged} of ${elapsedDays} elapsed days (${daysComplete} days with complete logging).`);

    if (avgPro >= (proTarget * 0.9)) {
      insights.push(`Your average protein intake (${avgPro}g) met your target (${proTarget}g).`);
    } else {
      insights.push(`Your average protein intake (${avgPro}g) was below your target of ${proTarget}g.`);
    }

    if (bestWaterDay && maxWaterMl > 0) {
      insights.push(`Your hydration was highest on ${bestWaterDay} (${Math.round(maxWaterMl)} ml).`);
    }

    if (totalBurned > 0) {
      insights.push(`You burned a total of ${Math.round(totalBurned)} kcal across ${activeDaysCount} active days (${totalActiveMins} active mins).`);
    }

    if (daysOverCal > 0) {
      insights.push(`Your calorie intake exceeded your target on ${daysOverCal} day${daysOverCal > 1 ? 's' : ''}.`);
    }
  }

  return {
    week_start: startStr,
    week_end: endStr,
    display_range: displayRange,
    has_data: hasData,
    is_offline: true,
    summary: {
      total_weekly_calories: Math.round(totalCal * 10) / 10,
      avg_daily_calories: avgCal,
      calorie_target: calTarget,
      total_protein_g: Math.round(totalPro * 10) / 10,
      avg_protein_g: avgPro,
      protein_target_g: proTarget,
      total_carbs_g: Math.round(totalCarb * 10) / 10,
      avg_carbs_g: avgCarb,
      total_fat_g: Math.round(totalFat * 10) / 10,
      avg_fat_g: avgFat,
      total_fiber_g: Math.round(totalFib * 10) / 10,
      avg_fiber_g: avgFib,
      total_water_ml: Math.round(totalWater),
      avg_water_ml: avgWater,
      water_target_ml: waterTarget,
      total_calories_burned: Math.round(totalBurned * 10) / 10,
      avg_daily_calories_burned: avgBurned,
      total_active_minutes: totalActiveMins,
      active_days: `${activeDaysCount}/${elapsedDays}`,
      active_days_count: activeDaysCount,
      total_meals_logged: totalMeals,
      days_with_complete_logging: daysComplete,
      days_with_missed_meals: daysMissed,
      goal_adherence_pct: adherencePct,
      elapsed_days: elapsedDays,
      avg_label: avgLabel
    },
    daily_breakdown: dailyBreakdown,
    insights: insights,
    empty_state_message: hasData ? null : "Not enough data to generate a weekly summary."
  };
};
