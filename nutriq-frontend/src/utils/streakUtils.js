/**
 * NutriQ Centralized Single Source of Truth for Streak Calculation
 * 
 * Calculates consecutive daily streaks, weekly activity (Monday to Sunday),
 * and longest streaks using user-specific local calendar dates (YYYY-MM-DD).
 * 
 * Guarantees strict user isolation and timezone safety.
 */
import { getToday, addDays, parseDateParts, getLocalDateFromTimestamp } from './dateUtils';

const DEFAULT_TIMEZONE = 'Asia/Kolkata';

/**
 * Calculates current streak, longest streak, total active days, and weekly activity
 * from actual user meal logs and nutrition activity.
 * 
 * @param {Array} meals - List of meal records
 * @param {Object} options - Optional configuration (userId, email, currentUser, timeZone, additionalDates, debug)
 * @returns {Object} streakData
 */
export const calculateCurrentStreak = (meals = [], options = {}) => {
  const currentUserId = options.userId || options.currentUser?.id || null;
  const currentUserEmail = options.email || options.currentUser?.email || null;
  const timeZone = options.timeZone || DEFAULT_TIMEZONE;
  const isDebug = Boolean(options.debug);

  // 1. Strict User Isolation: Filter meals for the currently authenticated user
  let rawList = Array.isArray(meals) ? meals : [];
  let userMeals = rawList;

  if (currentUserId || currentUserEmail) {
    userMeals = rawList.filter(m => {
      if (!m) return false;
      const mUid = m.user_id || m.userId;
      const mEmail = m.user_email || m.email;
      if (currentUserId && mUid) {
        return String(mUid) === String(currentUserId);
      }
      if (currentUserEmail && mEmail) {
        return String(mEmail).toLowerCase() === String(currentUserEmail).toLowerCase();
      }
      // If the meal object does not specify a user_id, assume it belongs to the active isolated store
      return true;
    });
  }

  // 2. Extract unique local calendar dates (YYYY-MM-DD)
  const activeDates = new Set();
  userMeals.forEach(m => {
    if (!m) return;
    const rawDate = m.occurred_at || m.date || m.created_at || m.timestamp;
    if (rawDate) {
      const localDateStr = getLocalDateFromTimestamp(rawDate, timeZone);
      if (localDateStr && localDateStr.length === 10) {
        activeDates.add(localDateStr);
      }
    }
  });

  // Additional activity dates if provided (e.g. water or exercise logs)
  if (Array.isArray(options.additionalDates)) {
    options.additionalDates.forEach(d => {
      if (d) {
        const localDateStr = getLocalDateFromTimestamp(d, timeZone);
        if (localDateStr && localDateStr.length === 10) {
          activeDates.add(localDateStr);
        }
      }
    });
  }

  const sortedMealDates = Array.from(activeDates).sort();
  const todayStr = getToday(timeZone);
  const completedToday = activeDates.has(todayStr);

  // 3. Compute consecutive active days
  // If today is completed -> count consecutive days backwards starting from today
  // If today is pending -> count consecutive days backwards starting from yesterday
  let consecutive = 0;
  let checkDateStr = completedToday ? todayStr : addDays(todayStr, -1);
  while (activeDates.has(checkDateStr)) {
    consecutive += 1;
    checkDateStr = addDays(checkDateStr, -1);
    if (consecutive > 3650) break;
  }

  // 4. Compute longest streak across all history
  let longestStreak = consecutive;
  if (sortedMealDates.length > 0) {
    let currentRun = 1;
    let maxRun = 1;
    for (let i = 1; i < sortedMealDates.length; i++) {
      const prev = sortedMealDates[i - 1];
      const curr = sortedMealDates[i];
      if (curr === addDays(prev, 1)) {
        currentRun += 1;
        if (currentRun > maxRun) maxRun = currentRun;
      } else if (curr !== prev) {
        currentRun = 1;
      }
    }
    longestStreak = Math.max(longestStreak, maxRun);
  }

  // 5. Generate current week's Monday to Sunday activity
  const todayParts = parseDateParts(todayStr);
  const todayObj = new Date(todayParts.year, todayParts.month - 1, todayParts.day, 12, 0, 0);
  const dayOfWeek = (todayObj.getDay() + 6) % 7; // 0=Mon, 1=Tue, ..., 6=Sun
  const mondayStr = addDays(todayStr, -dayOfWeek);

  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const dayInitials = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
  const weeklyHistory = [];
  for (let i = 0; i < 7; i++) {
    const dStr = addDays(mondayStr, i);
    const isDToday = dStr === todayStr;
    const isDFuture = dStr > todayStr;
    const isDone = isDFuture ? false : activeDates.has(dStr);
    weeklyHistory.push({
      date: dStr,
      day_name: dayNames[i],
      day_initial: dayInitials[i],
      completed: isDone,
      logged: isDone,
      is_today: isDToday,
      is_future: isDFuture
    });
  }

  if (isDebug) {
    console.log("Current user:", options.currentUser || { id: currentUserId, email: currentUserEmail });
    console.log("User meal dates:", sortedMealDates);
    console.log("Calculated current streak:", consecutive);
  }

  return {
    current_streak: consecutive,
    longest_streak: longestStreak,
    total_active_days: activeDates.size,
    last_completed_date: completedToday ? todayStr : (consecutive > 0 ? addDays(todayStr, -1) : null),
    completed_today: completedToday,
    weekly_history: weeklyHistory,
    user_meal_dates: sortedMealDates,
    new_milestone: null,
    milestones_achieved: []
  };
};
