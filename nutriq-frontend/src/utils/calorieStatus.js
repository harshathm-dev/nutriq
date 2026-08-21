/**
 * NutriQ Centralized Calorie Balance and Weight-Loss Status Logic
 * 
 * Defines standard status rules matching the backend NutritionEngine.
 * Clearly distinguishes:
 * A. Food Consumed
 * B. Daily Calorie Target
 * C. Physical Activity Calories Burned
 * 
 * Does NOT double-count or subtract exercise from the food target if the target already incorporates activity (TDEE).
 */

export const CALORIE_STATUS_CONFIG = {
  very_low_ratio: 0.50,       // <50% of target is flagged as Very Low Intake
  below_target_ratio: 0.85,    // <85% of target is flagged as Below Target
  weight_loss: {
    lower_ratio: 0.85,
    upper_surplus: 50.0,      // > target + 50 kcal is Target Exceeded
    slight_excess_max: 250.0
  },
  maintenance: {
    lower_ratio: 0.85,
    upper_surplus: 150.0
  },
  weight_gain: {
    lower_ratio: 0.85,
    upper_surplus: 250.0
  },
  muscle_building: {
    lower_ratio: 0.85,
    upper_surplus: 250.0
  }
};

export const calculateCalorieStatus = ({
  targetCalories = 2000,
  consumedCalories = 0,
  burnedCalories = 0,
  goalType = 'weight_loss',
  hasMeals = true
}) => {
  const target = Math.round(parseFloat(targetCalories) || 2000);
  const consumed = Math.round(parseFloat(consumedCalories) || 0);
  const burned = Math.round(parseFloat(burnedCalories) || 0);
  const remaining = Math.max(0, target - consumed);
  const surplus = Math.max(0, consumed - target);
  const percentage = target > 0 ? Math.round((consumed / target) * 1000) / 10 : 0;
  const goalLower = (goalType || 'maintain').toLowerCase();

  // 0. If no meals logged yet
  if (!hasMeals || consumed === 0) {
    let msg = "No meals logged yet today. Log your meals to track your daily calorie balance and progress.";
    if (burned > 0) {
      msg += ` You have also logged ${burned.toLocaleString()} kcal of physical activity.`;
    }
    return {
      status: 'no_meals',
      statusLevel: 'no_meals',
      statusBadge: 'No Meals Logged Yet',
      label: 'No Meals Logged Yet',
      icon: '⚪',
      color: 'var(--text-muted)',
      badgeClass: 'badge-gray',
      message: msg,
      warningTitle: null,
      warningMessage: null,
      whyItMatters: null,
      positiveFeedback: burned === 0 ? "Ready to log your first meal today." : `You've logged ${burned.toLocaleString()} kcal of physical activity today. Ready to log your meals.`,
      consumed,
      target,
      remaining,
      burned,
      percentage,
      surplus: 0,
      netEnergyAfterExercise: consumed - burned
    };
  }

  // 1. VERY LOW INTAKE: Consumed < 50% of target
  if (percentage < (CALORIE_STATUS_CONFIG.very_low_ratio * 100)) {
    const exerciseNote = burned > 0 ? ` You've also logged ${burned.toLocaleString()} kcal of physical activity.` : '';
    const msg = `Your calorie intake is unusually low today (${consumed.toLocaleString()} / ${target.toLocaleString()} kcal). If you haven't finished eating for the day, consider a nourishing meal that supports your daily energy and protein needs.${exerciseNote} Please consult a qualified nutrition professional for individualized guidance.`;
    return {
      status: 'very_low',
      statusLevel: 'very_low',
      statusBadge: 'Very Low Intake',
      label: '🔴 Very Low Intake',
      icon: '🔴',
      color: '#ef4444',
      badgeClass: 'badge-red',
      message: msg,
      warningTitle: 'Unusually Low Calorie Intake',
      warningMessage: msg,
      whyItMatters: 'Consistently consuming far below your energy needs can lead to fatigue, nutrient deficiencies, and muscle loss.',
      positiveFeedback: null,
      consumed,
      target,
      remaining,
      burned,
      percentage,
      surplus: 0,
      netEnergyAfterExercise: consumed - burned
    };
  }

  // 2. BELOW TARGET: 50% <= percentage < 85%
  if (percentage < (CALORIE_STATUS_CONFIG.below_target_ratio * 100)) {
    const exerciseNote = burned > 0 ? ` You've also logged ${burned.toLocaleString()} kcal of physical activity.` : '';
    const msg = `You've consumed ${consumed.toLocaleString()} kcal of your ${target.toLocaleString()} kcal target (${remaining.toLocaleString()} kcal remaining).${exerciseNote} Consider a balanced meal if you have not finished eating for the day.`;
    return {
      status: 'below_target',
      statusLevel: 'below_target',
      statusBadge: "Below Today's Target",
      label: "🟡 Below Today's Target",
      icon: '🟡',
      color: '#f59e0b',
      badgeClass: 'badge-amber',
      message: msg,
      warningTitle: "Below Today's Target",
      warningMessage: msg,
      whyItMatters: 'Meeting your intended weight-loss target range ensures steady progress while preserving lean muscle mass and daily energy.',
      positiveFeedback: null,
      consumed,
      target,
      remaining,
      burned,
      percentage,
      surplus: 0,
      netEnergyAfterExercise: consumed - burned
    };
  }

  // 3. TARGET EXCEEDED
  let excessMargin = CALORIE_STATUS_CONFIG.weight_loss.upper_surplus;
  let goalDesc = 'weight-loss';
  if (goalLower.includes('maintain')) {
    excessMargin = CALORIE_STATUS_CONFIG.maintenance.upper_surplus;
    goalDesc = 'maintenance';
  } else if (goalLower.includes('gain') || goalLower.includes('muscle')) {
    excessMargin = CALORIE_STATUS_CONFIG.weight_gain.upper_surplus;
    goalDesc = 'daily';
  }

  if (consumed > (target + excessMargin)) {
    const msg = `You've exceeded today's ${goalDesc} calorie target by ${surplus.toLocaleString()} kcal. If this happens consistently, it may make your ${goalDesc} goal more difficult.`;
    return {
      status: 'target_exceeded',
      statusLevel: 'target_exceeded',
      statusBadge: 'Target Exceeded',
      label: '🟠 Target Exceeded',
      icon: '🟠',
      color: '#f97316',
      badgeClass: 'badge-orange',
      message: msg,
      warningTitle: 'Above Calorie Target',
      warningMessage: msg,
      whyItMatters: 'A single day of higher intake does not cause immediate weight gain. Focus on hydration, fiber, and nutritional balance for upcoming meals.',
      positiveFeedback: null,
      consumed,
      target,
      remaining: 0,
      burned,
      percentage,
      surplus,
      netEnergyAfterExercise: consumed - burned
    };
  }

  // 4. ON TRACK
  const exerciseNote = burned > 0 ? ` (along with ${burned.toLocaleString()} kcal burned from physical activity)` : '';
  const msg = `You are on track with today's calorie target (${consumed.toLocaleString()} / ${target.toLocaleString()} kcal)${exerciseNote}.`;
  return {
    status: 'on_track',
    statusLevel: 'on_track',
    statusBadge: 'On Track',
    label: '🟢 On Track',
    icon: '🟢',
    color: '#10b981',
    badgeClass: 'badge-emerald',
    message: msg,
    warningTitle: null,
    warningMessage: null,
    whyItMatters: null,
    positiveFeedback: "Great! You're within your calorie target today.",
    consumed,
    target,
    remaining,
    burned,
    percentage,
    surplus: 0,
    netEnergyAfterExercise: consumed - burned
  };
};
