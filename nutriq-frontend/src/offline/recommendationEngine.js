import { db } from './db.js';
import { calculateLocalDailySummary } from './nutritionCalculator.js';
import { calculateCalorieStatus } from '../utils/calorieStatus.js';
import { getToday, getLocalDate, isToday, isFuture } from '../utils/dateUtils.js';

const ALLERGEN_KEYWORDS = {
  dairy: ["milk", "curd", "paneer", "ghee", "butter", "cheese", "yogurt", "buttermilk", "lassi", "whey", "dahi"],
  lactose: ["milk", "curd", "paneer", "ghee", "butter", "cheese", "yogurt", "buttermilk", "lassi", "whey", "dahi"],
  gluten: ["wheat", "roti", "chapati", "parotta", "paratha", "bread", "pasta", "maida", "semolina", "rava", "sooji", "poori", "naan"],
  wheat: ["wheat", "roti", "chapati", "parotta", "paratha", "bread", "pasta", "maida", "semolina", "rava", "sooji", "poori", "naan"],
  peanut: ["peanut", "groundnut", "kadala", "kadalai"],
  peanuts: ["peanut", "groundnut", "kadala", "kadalai"],
  "tree nuts": ["almond", "badam", "cashew", "kaju", "walnut", "pista", "pistachio"],
  nuts: ["peanut", "groundnut", "almond", "badam", "cashew", "kaju", "walnut", "pista", "pistachio"],
  egg: ["egg", "omelet", "omelette", "boiled egg", "egg bhurji"],
  eggs: ["egg", "omelet", "omelette", "boiled egg", "egg bhurji"],
  fish: ["fish", "meen", "salmon", "tuna", "pomfret", "sardine", "mackerel"],
  shellfish: ["prawn", "shrimp", "crab", "lobster"],
  seafood: ["fish", "meen", "prawn", "shrimp", "crab", "lobster", "salmon", "tuna"],
  soy: ["soy", "soya", "tofu", "edamame"],
  soya: ["soy", "soya", "tofu", "edamame"]
};

const NON_VEG_KEYWORDS = ["chicken", "mutton", "fish", "prawn", "shrimp", "crab", "egg", "meat", "beef", "pork", "meen", "biryani with chicken", "chicken curry", "mutton curry", "fish curry"];
const NON_VEGAN_KEYWORDS = [...NON_VEG_KEYWORDS, "milk", "curd", "paneer", "ghee", "butter", "cheese", "yogurt", "buttermilk", "lassi", "honey", "whey", "dahi"];

export const evaluateOfflineNutritionStatus = async (dateStr = null, mealType = null) => {
  const targetDateStr = dateStr || getToday();

  const [allMeals, waterLogs, exerciseLogs, profile, targets, foods] = await Promise.all([
    db.meals.toArray(),
    db.water_logs.toArray(),
    db.exercise_logs ? db.exercise_logs.toArray() : [],
    db.profile.toCollection().first(),
    db.targets ? db.targets.toCollection().first() : null,
    db.foods.toArray()
  ]);

  const dailySummary = calculateLocalDailySummary(allMeals, waterLogs, profile, targets, targetDateStr, exerciseLogs);
  const calConsumed = dailySummary.calories.consumed;
  const calTarget = dailySummary.calories.target;
  const calBurned = dailySummary.calories.burned || 0;
  const calDiff = Math.round((calConsumed - calTarget) * 10) / 10;
  const calRemaining = dailySummary.calories.remaining;

  const proConsumed = dailySummary.macros.protein.consumed;
  const proTarget = dailySummary.macros.protein.target;
  const carbConsumed = dailySummary.macros.carbohydrates.consumed;
  const carbTarget = dailySummary.macros.carbohydrates.target;
  const fatConsumed = dailySummary.macros.fat.consumed;
  const fatTarget = dailySummary.macros.fat.target;
  const fibConsumed = dailySummary.macros.fiber.consumed;
  const fibTarget = dailySummary.macros.fiber.target;

  const fitnessGoal = (profile?.fitness_goal || 'maintain').toLowerCase();
  const goalDisplay = (profile?.fitness_goal || 'Maintain').replace('_', ' ');
  const hasMealsLogged = calConsumed > 0;

  // Centralized Calorie Status
  const calStatusData = calculateCalorieStatus({
    targetCalories: calTarget,
    consumedCalories: calConsumed,
    burnedCalories: calBurned,
    goalType: fitnessGoal,
    hasMeals: hasMealsLogged
  });

  const statusLevel = calStatusData.statusLevel;
  const statusBadge = calStatusData.statusBadge;
  const warningTitle = calStatusData.warningTitle;
  const warningMessage = calStatusData.warningMessage;
  const whyItMatters = calStatusData.whyItMatters;
  const positiveFeedback = calStatusData.positiveFeedback;

  // Separate Protein Evaluation
  let proteinStatus = 'on_track';
  let proteinWarning = null;
  if (proTarget > 0) {
    const proPct = (proConsumed / proTarget) * 100;
    if (proPct < 60 && calConsumed >= (calTarget * 0.4)) {
      proteinStatus = 'below_target';
      proteinWarning = `Your protein intake (${proConsumed}g / ${proTarget}g) is below today's target. Consider adding a protein-rich food option to your next meal.`;
    }
  }

  // Generate Recommendations
  const dietPref = (profile?.dietary_preference || 'standard').toLowerCase();
  const userAllergies = Array.isArray(profile?.allergies) ? profile.allergies.map(a => a.toLowerCase()) : [];

  let targetSlot = mealType;
  if (!targetSlot) {
    const nowHour = new Date().getHours();
    if (nowHour < 11) targetSlot = 'breakfast';
    else if (nowHour < 16) targetSlot = 'lunch';
    else if (nowHour < 19) targetSlot = 'snack';
    else targetSlot = 'dinner';
  }

  const recommendations = [];
  const candidatePool = Array.isArray(foods) && foods.length > 0 ? foods : [];

  const filteredCandidates = candidatePool.filter(food => {
    const nameLower = (food.name || '').toLowerCase();
    const catLower = (food.category || '').toLowerCase();

    // Allergy check
    for (const allergy of userAllergies) {
      const kws = ALLERGEN_KEYWORDS[allergy] || [allergy];
      if (kws.some(kw => nameLower.includes(kw) || catLower.includes(kw))) {
        return false;
      }
    }

    // Diet check
    if (dietPref.includes('veg') && !dietPref.includes('non')) {
      if (NON_VEG_KEYWORDS.some(kw => nameLower.includes(kw)) || catLower.includes('non') || catLower.includes('chicken') || catLower.includes('fish') || catLower.includes('egg')) {
        return false;
      }
    }

    if (dietPref.includes('vegan')) {
      if (NON_VEGAN_KEYWORDS.some(kw => nameLower.includes(kw)) || catLower.includes('dairy') || catLower.includes('meat')) {
        return false;
      }
    }

    return true;
  });

  if (statusLevel === 'target_exceeded') {
    const lightFoods = filteredCandidates.filter(f => (f.calories || 0) <= 150);
    lightFoods.sort((a, b) => (b.fiber_g || 0) - (a.fiber_g || 0));
    for (const f of lightFoods.slice(0, 4)) {
      recommendations.push({
        food_id: f.id,
        food_name: f.name,
        meal_type: targetSlot,
        serving_label: f.serving_label || '1 serving',
        calories: f.calories,
        protein_g: f.protein_g,
        carbs_g: f.carbs_g,
        fat_g: f.fat_g,
        fiber_g: f.fiber_g,
        suitability_score: 0.85,
        recommendation_source: 'offline_engine',
        dietary_tags: ['Offline Ready'],
        reason: 'Light, nutrient-dense option that provides fiber and hydration without adding excess calories.'
      });
    }
  } else if (statusLevel === 'below_target' || statusLevel === 'very_low') {
    const budget = Math.max(200, calRemaining);
    const suitable = filteredCandidates.filter(f => (f.calories || 0) <= budget);
    suitable.sort((a, b) => ((b.protein_g || 0) * 1.5 + (b.fiber_g || 0)) - ((a.protein_g || 0) * 1.5 + (a.fiber_g || 0)));
    for (const f of suitable.slice(0, 4)) {
      recommendations.push({
        food_id: f.id,
        food_name: f.name,
        meal_type: targetSlot,
        serving_label: f.serving_label || '1 serving',
        calories: f.calories,
        protein_g: f.protein_g,
        carbs_g: f.carbs_g,
        fat_g: f.fat_g,
        fiber_g: f.fiber_g,
        suitability_score: 0.88,
        recommendation_source: 'offline_engine',
        dietary_tags: ['Offline Ready'],
        reason: `Nourishing choice (${f.calories} kcal, ${f.protein_g}g protein) to help reach your target and support lean muscle.`
      });
    }
  } else {
    const budget = Math.max(150, calRemaining + 50);
    const fitting = filteredCandidates.filter(f => (f.calories || 0) <= budget);
    fitting.sort((a, b) => ((b.fiber_g || 0) * 2 + (b.protein_g || 0)) - ((a.fiber_g || 0) * 2 + (a.protein_g || 0)));
    for (const f of fitting.slice(0, 4)) {
      recommendations.push({
        food_id: f.id,
        food_name: f.name,
        meal_type: targetSlot,
        serving_label: f.serving_label || '1 serving',
        calories: f.calories,
        protein_g: f.protein_g,
        carbs_g: f.carbs_g,
        fat_g: f.fat_g,
        fiber_g: f.fiber_g,
        suitability_score: 0.82,
        recommendation_source: 'offline_engine',
        dietary_tags: ['Offline Ready'],
        reason: `Fits your remaining budget (${f.calories} kcal) with balanced fiber and protein.`
      });
    }
  }

  return {
    date: targetDateStr,
    goal: fitnessGoal,
    goal_display: goalDisplay,
    daily_calorie_target: calTarget,
    calories_consumed: calConsumed,
    calories_burned: calBurned,
    calories_remaining: calRemaining,
    calorie_difference: calDiff,
    net_energy_after_exercise: calConsumed - calBurned,
    status_level: statusLevel,
    status_badge: statusBadge,
    calorie_status: calStatusData,
    warning_title: warningTitle,
    warning_message: warningMessage,
    why_it_matters: whyItMatters,
    positive_feedback: positiveFeedback,
    protein_status: proteinStatus,
    protein_warning: proteinWarning,
    weekly_pattern_warning: null,
    has_meals_logged: hasMealsLogged,
    recommendations: recommendations,
    macros: {
      protein: { consumed: proConsumed, target: proTarget, remaining: Math.max(0, proTarget - proConsumed), percentage: Math.round((proConsumed / proTarget) * 100), status: proteinStatus },
      carbohydrates: { consumed: carbConsumed, target: carbTarget, remaining: Math.max(0, carbTarget - carbConsumed), percentage: Math.round((carbConsumed / carbTarget) * 100) },
      fat: { consumed: fatConsumed, target: fatTarget, remaining: Math.max(0, fatTarget - fatConsumed), percentage: Math.round((fatConsumed / fatTarget) * 100) },
      fiber: { consumed: fibConsumed, target: fibTarget, remaining: Math.max(0, fibTarget - fibConsumed), percentage: Math.round((fibConsumed / fibTarget) * 100) }
    }
  };
};

export const calculateLocalSmartRecommendations = async (dateStr = null, mealType = null, limit = 4) => {
  const statusRes = await evaluateOfflineNutritionStatus(dateStr, mealType);
  const remCal = statusRes.calories_remaining || 0;
  const remPro = statusRes.macros?.protein?.remaining || 0;
  const remCarb = statusRes.macros?.carbohydrates?.remaining || 0;
  const remFat = statusRes.macros?.fat?.remaining || 0;
  const remFib = statusRes.macros?.fiber?.remaining || 0;
  const remWaterL = statusRes.hydration?.remaining_l !== undefined ? statusRes.hydration.remaining_l : 0.5;

  const proTarget = statusRes.macros?.protein?.target || 100;
  const calTarget = statusRes.daily_calorie_target || 2000;
  const carbConsumed = statusRes.macros?.carbohydrates?.consumed || 0;
  const carbTarget = statusRes.macros?.carbohydrates?.target || 250;
  const calConsumed = statusRes.calories_consumed || 0;

  const proGap = remPro > proTarget * 0.45 ? 'HIGH' : (remPro > 15 ? 'MODERATE' : (remPro > 0 ? 'LOW' : 'MET'));
  const calGap = remCal > calTarget * 0.45 ? 'HIGH' : (remCal > 200 ? 'MODERATE' : (remCal > 0 ? 'LOW' : 'MET'));
  const fibGap = remFib > 10 ? 'HIGH' : (remFib > 4 ? 'MODERATE' : 'MET');
  const fatGap = remFat > 10 ? 'MODERATE' : 'MET';
  const hydrationGap = remWaterL <= 0.5 ? 'NEAR TARGET' : (remWaterL <= 1.5 ? 'MODERATE' : 'HIGH');

  const isCurrentDay = !dateStr || isToday(dateStr);
  const isFutureDay = Boolean(dateStr && isFuture(dateStr));
  const isEmptyDay = !statusRes.has_meals_logged;

  const warnings = [];
  if (calConsumed >= calTarget) {
    warnings.append ? warnings.push({
      type: 'calories_exceeded',
      title: 'Calorie Target Reached',
      message: 'You have reached your daily calorie target. Consider lower-calorie, nutrient-dense options for your next meal.'
    }) : warnings.push({
      type: 'calories_exceeded',
      title: 'Calorie Target Reached',
      message: 'You have reached your daily calorie target. Consider lower-calorie, nutrient-dense options for your next meal.'
    });
  } else if (!isEmptyDay && !isFutureDay && calConsumed < (calTarget * 0.70)) {
    warnings.push({
      type: 'below_target',
      title: 'Calorie Intake Below Target',
      message: 'Your calorie intake is currently below your daily target. Consider a balanced meal to support your goal and energy needs.'
    });
  }

  if (carbConsumed >= carbTarget) {
    warnings.push({
      type: 'carbs_exceeded',
      title: 'Carbohydrates Reached Target',
      message: "Your carbohydrate intake has reached today's target. Prioritize protein, fiber and nutrient-dense foods for your next meal."
    });
  }

  if (!isEmptyDay && !isFutureDay && remPro > (proTarget * 0.45)) {
    warnings.push({
      type: 'low_protein',
      title: 'Protein Intake Low',
      message: 'Your protein intake is low today. Consider adding a protein-rich food to help meet your daily target.'
    });
  }

  let message = null;
  if (isFutureDay) {
    message = "Future date selected. Suggestions are tailored for your overall wellness goal.";
  } else if (isEmptyDay) {
    message = `Start logging today's meals to get personalized nutrition recommendations tailored to your ${statusRes.goal_display} goal.`;
  } else if (carbConsumed >= carbTarget) {
    message = "Carbohydrate target reached. High-protein and fiber-rich options prioritized.";
  } else if (proGap === 'HIGH') {
    message = "High-protein choices prioritized to help close today's protein deficit within your calorie budget.";
  } else if (calGap === 'LOW') {
    message = "Light, nutrient-dense suggestions matching your remaining calorie budget.";
  } else {
    message = `Personalized suggestions based on today's intake and your ${statusRes.goal_display} goal.`;
  }

  return {
    recommendations: (statusRes.recommendations || []).slice(0, limit).map(r => ({
      ...r,
      food_name: r.food_name || r.name,
      serving_quantity: r.serving_quantity || 1.0,
      serving_unit: r.serving_unit || r.serving_label || 'serving',
      grams: r.grams || 100,
      score: r.suitability_score || 0.85
    })),
    remaining_needs: {
      calories: remCal,
      protein_g: remPro,
      carbs_g: remCarb,
      fat_g: remFat,
      fiber_g: remFib,
      water_l: remWaterL
    },
    gaps: {
      protein: proGap,
      calories: calGap,
      fiber: fibGap,
      fat: fatGap,
      hydration: hydrationGap
    },
    goal: statusRes.goal,
    goal_display: statusRes.goal_display,
    target_meal_type: mealType || 'snack',
    is_empty_day: isEmptyDay,
    is_future: isFutureDay,
    message: message,
    warnings: warnings
  };
};
