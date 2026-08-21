import { db, ensureDbOpen, enqueueOfflineAction } from '../offline/db.js';
import { calculateLocalDailySummary, calculateLocalWeeklySummary } from '../offline/nutritionCalculator.js';
import { evaluateOfflineNutritionStatus, calculateLocalSmartRecommendations } from '../offline/recommendationEngine.js';
import { reportGenerator } from './reportGenerator.js';
import { getToday, getLocalDate, getLocalDateFromTimestamp, formatDate, parseDateParts, addDays } from '../utils/dateUtils.js';
import { calculateCurrentStreak } from '../utils/streakUtils.js';

const getApiBaseUrl = () => {
  const envUrl = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_BASE_URL : null;
  let url = (envUrl && typeof envUrl === 'string') ? envUrl.trim() : 'http://localhost:8000/api';
  // Strip trailing slashes
  url = url.replace(/\/+$/, '');
  // Normalize so that /api is always the suffix
  if (!url.endsWith('/api')) {
    url = `${url}/api`;
  }
  return url;
};

export const API_BASE_URL = getApiBaseUrl();
export const API_BASE = API_BASE_URL;

export const safeFetch = async (url, options = {}) => {
  try {
    return await fetch(url, options);
  } catch (err) {
    if (err.name === 'TypeError' && (err.message?.includes('fetch') || err.message?.includes('NetworkError') || err.message?.includes('Load failed'))) {
      const error = new Error(`Cannot connect to NutriQ server at ${API_BASE}. If using Render, the backend may take 30-50s to wake up from idle. Please wait a moment and try again.`);
      error.isNetworkError = true;
      error.originalError = err;
      throw error;
    }
    throw err;
  }
};

const getAuthHeaders = () => {
  const token = localStorage.getItem('nutriq_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
};

const parseError = async (res, defaultMsg) => {
  let detail = null;
  try {
    const contentType = res?.headers?.get ? (res.headers.get('content-type') || '') : '';
    if (contentType.includes('application/json')) {
      const err = await res.json();
      if (typeof err.detail === 'string') detail = err.detail;
      else if (Array.isArray(err.detail)) detail = err.detail.map(d => d.msg || d.loc?.join('.')).join(', ');
      else if (err.message) detail = err.message;
      else if (err.error) detail = typeof err.error === 'string' ? err.error : JSON.stringify(err.error);
    } else {
      const text = await res.text();
      if (text && text.length < 200 && !text.includes('<!DOCTYPE') && !text.includes('<html')) {
        detail = text;
      }
    }
  } catch (e) {}

  if (detail) {
    if (detail.toLowerCase() === 'not found') {
      return `Endpoint not found on backend (HTTP 404 at ${res?.url || API_BASE}). Please check the API URL configuration.`;
    }
    return detail;
  }

  const code = res?.status;
  if (code === 400) return defaultMsg || "Bad Request (HTTP 400): Please check the entered data.";
  if (code === 401) return "Invalid email or password, or session expired (HTTP 401).";
  if (code === 403) return "Access Denied (HTTP 403): You do not have permission for this request.";
  if (code === 404) return `Endpoint not found on backend (HTTP 404 at ${res?.url || API_BASE}).`;
  if (code === 409) return "An account with this email address already exists. Please sign in instead.";
  if (code === 422) return "Validation Error (HTTP 422): Submitted data did not match expected format.";
  if (code === 429) return "Rate limit exceeded (HTTP 429). Please wait a moment before trying again.";
  if (code >= 500) return `Backend Server Error (HTTP ${code}): The server encountered an issue. Please retry shortly.`;

  return defaultMsg || `Request failed (HTTP ${code || 'Unknown'})`;
};

export const normalizeMeal = (m) => {
  if (!m) return null;
  const items = (m.items || []).map(i => {
    const qty = Number(i.quantity !== undefined && i.quantity !== null ? i.quantity : (i.portion !== undefined && i.portion !== null ? i.portion : 1));
    const foodName = i.food_name || i.name || 'Food item';
    const grams = Number(i.grams || 100);
    const cal = Number(i.calories || 0);
    const pro = Number(i.protein_g !== undefined ? i.protein_g : (i.protein !== undefined ? i.protein : 0));
    const carb = Number(i.carbs_g !== undefined ? i.carbs_g : (i.carbs !== undefined ? i.carbs : 0));
    const fat = Number(i.fat_g !== undefined ? i.fat_g : (i.fat !== undefined ? i.fat : 0));
    const fib = Number(i.fiber_g !== undefined ? i.fiber_g : (i.fiber !== undefined ? i.fiber : 0));

    return {
      ...i,
      id: i.id || ('item_' + Math.random().toString(36).substring(2, 8)),
      food_id: i.food_id || i.foodId || null,
      food_name: foodName,
      name: foodName,
      quantity: qty,
      portion: qty,
      serving_unit: i.serving_unit || i.servingUnit || 'serving',
      grams: grams,
      calories: cal,
      protein_g: pro,
      protein: pro,
      carbs_g: carb,
      carbs: carb,
      fat_g: fat,
      fat: fat,
      fiber_g: fib,
      fiber: fib
    };
  });

  const totCal = Number(
    m.totals?.calories !== undefined ? m.totals.calories :
    (m.total_calories !== undefined ? m.total_calories :
    (m.calories !== undefined ? m.calories :
    items.reduce((acc, it) => acc + (it.calories || 0), 0)))
  );

  const totPro = Number(
    m.totals?.protein_g !== undefined ? m.totals.protein_g :
    (m.total_protein !== undefined ? m.total_protein :
    (m.protein !== undefined ? m.protein :
    items.reduce((acc, it) => acc + (it.protein_g || 0), 0)))
  );

  const totCarb = Number(
    m.totals?.carbs_g !== undefined ? m.totals.carbs_g :
    (m.total_carbs !== undefined ? m.total_carbs :
    (m.carbs !== undefined ? m.carbs :
    items.reduce((acc, it) => acc + (it.carbs_g || 0), 0)))
  );

  const totFat = Number(
    m.totals?.fat_g !== undefined ? m.totals.fat_g :
    (m.total_fat !== undefined ? m.total_fat :
    (m.fat !== undefined ? m.fat :
    items.reduce((acc, it) => acc + (it.fat_g || 0), 0)))
  );

  const totFib = Number(
    m.totals?.fiber_g !== undefined ? m.totals.fiber_g :
    (m.total_fiber !== undefined ? m.total_fiber :
    (m.fiber !== undefined ? m.fiber :
    items.reduce((acc, it) => acc + (it.fiber_g || 0), 0)))
  );

  const mealDate = m.date || m.meal_date || getLocalDateFromTimestamp(m.occurred_at) || getToday();
  const mealTime = m.time || m.meal_time || m.logged_time || (m.occurred_at ? (typeof m.occurred_at === 'string' ? m.occurred_at.substring(11, 16) : '') : '12:00');
  const mealType = m.meal_type || 'breakfast';

  return {
    ...m,
    id: m.id,
    meal_type: mealType,
    name: m.name || mealType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
    occurred_at: m.occurred_at || new Date().toISOString(),
    date: mealDate,
    meal_date: mealDate,
    time: mealTime,
    meal_time: mealTime,
    logged_time: mealTime,
    items: items,
    totals: {
      calories: Math.round(totCal * 10) / 10,
      protein_g: Math.round(totPro * 10) / 10,
      carbs_g: Math.round(totCarb * 10) / 10,
      fat_g: Math.round(totFat * 10) / 10,
      fiber_g: Math.round(totFib * 10) / 10
    },
    total_calories: Math.round(totCal),
    calories: Math.round(totCal),
    total_protein: Math.round(totPro * 10) / 10,
    protein: Math.round(totPro * 10) / 10,
    total_carbs: Math.round(totCarb * 10) / 10,
    carbs: Math.round(totCarb * 10) / 10,
    total_fat: Math.round(totFat * 10) / 10,
    fat: Math.round(totFat * 10) / 10,
    total_fiber: Math.round(totFib * 10) / 10,
    fiber: Math.round(totFib * 10) / 10
  };
};

export const api = {
  // Auth
  register: async (data) => {
    const res = await safeFetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const msg = await parseError(res, 'Registration failed');
      throw new Error(msg);
    }
    return res.json();
  },

  login: async (email, password) => {
    const res = await safeFetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) {
      const msg = await parseError(res, 'Login failed');
      throw new Error(msg);
    }
    return res.json();
  },

  getGoogleAuthUrl: () => {
    return `${API_BASE}/auth/google`;
  },

  googleLogin: async ({ credential = null, accessToken = null, email = null, name = null, googleId = null } = {}) => {
    try {
      const res = await safeFetch(`${API_BASE}/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          credential,
          access_token: accessToken,
          email,
          name,
          google_id: googleId
        })
      });
      if (!res.ok) {
        const msg = await parseError(res, 'Google sign-in was unsuccessful. Please try again.');
        throw new Error(msg);
      }
      return res.json();
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error("Unable to connect to the NutriQ server. Please ensure the backend is running.");
      }
      throw err;
    }
  },

  logout: async () => {
    try {
      await safeFetch(`${API_BASE}/auth/logout`, { method: 'POST', headers: getAuthHeaders() });
    } catch (e) {}
    localStorage.removeItem('nutriq_token');
    localStorage.removeItem('nutriq_email');
    localStorage.removeItem('nutriq_user_id');
    return { success: true };
  },

  forgotPassword: async (email) => {
    const res = await safeFetch(`${API_BASE}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim().toLowerCase() })
    });
    if (!res.ok) {
      const msg = await parseError(res, 'Failed to process password reset request.');
      throw new Error(msg);
    }
    return res.json();
  },

  validateResetToken: async (token) => {
    const res = await safeFetch(`${API_BASE}/auth/validate-reset-token?token=${encodeURIComponent(token)}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) {
      return { valid: false, reason: 'invalid' };
    }
    return res.json();
  },

  resetPassword: async (token, newPassword) => {
    const res = await safeFetch(`${API_BASE}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token.trim(), new_password: newPassword })
    });
    if (!res.ok) {
      const msg = await parseError(res, 'Password reset failed. Please request a new link.');
      throw new Error(msg);
    }
    return res.json();
  },

  // Profile & Goals
  createProfile: async (data) => {
    try {
      const res = await safeFetch(`${API_BASE}/profile`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data)
      });
      if (res.ok) {
        const saved = await res.json();
        try {
          await ensureDbOpen();
          if (db.isOpen()) {
            await db.profile.put(saved);
          }
        } catch (storageErr) {
          console.warn("Could not cache profile to offline DB:", storageErr);
        }
        return saved;
      }
      const msg = await parseError(res, "Failed to create profile");
      throw new Error(msg);
    } catch (e) {
      if (e.message && !e.message.toLowerCase().includes('failed to fetch') && !e.message.toLowerCase().includes('network')) {
        throw e;
      }
      console.warn("Offline profile creation fallback:", e);
    }
    try {
      await ensureDbOpen();
      if (db.isOpen()) {
        await db.profile.put(data);
      }
      await enqueueOfflineAction('profile', data.id || 'prof_local', 'CREATE', data);
    } catch (e) {
      console.warn("Could not save profile offline:", e);
    }
    return data;
  },

  getProfile: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/profile`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (data) {
          try {
            await ensureDbOpen();
            if (db.isOpen()) {
              await db.profile.put(data);
            }
          } catch (storageErr) {
            console.warn("Could not cache profile to offline DB:", storageErr);
          }
        }
        return data;
      }
    } catch (e) {
      console.warn("Offline fallback for user profile");
    }
    try {
      await ensureDbOpen();
      if (db.isOpen()) {
        return await db.profile.toCollection().first();
      }
    } catch (e) {
      console.warn("Could not read profile from offline DB:", e);
    }
    return null;
  },

  updateProfile: async (data) => {
    try {
      const res = await safeFetch(`${API_BASE}/profile`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data)
      });
      if (res.ok) {
        const saved = await res.json();
        try {
          await ensureDbOpen();
          if (db.isOpen()) {
            await db.profile.put(saved);
          }
        } catch (storageErr) {
          console.warn("Could not cache updated profile to offline DB:", storageErr);
        }
        return saved;
      }
      const msg = await parseError(res, "Failed to update profile");
      throw new Error(msg);
    } catch (e) {
      if (e.message && !e.message.toLowerCase().includes('failed to fetch') && !e.message.toLowerCase().includes('network')) {
        throw e;
      }
      console.warn("Offline profile save");
    }
    try {
      await ensureDbOpen();
      if (db.isOpen()) {
        await db.profile.put(data);
      }
      await enqueueOfflineAction('profile', data.id || 'prof_local', 'UPDATE', data);
    } catch (e) {
      console.warn("Could not save profile offline:", e);
    }
    return data;
  },

  getGoal: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/goals`, { headers: getAuthHeaders() });
      if (res.ok) {
        const goals = await res.json();
        return Array.isArray(goals) && goals.length > 0 ? goals[0] : null;
      }
    } catch (e) {
      console.warn("Offline goal fallback");
    }
    return null;
  },

  createGoal: async (goalData) => {
    const res = await safeFetch(`${API_BASE}/goals`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(goalData)
    });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to set goal");
      throw new Error(msg);
    }
    return res.json();
  },

  setGoal: async (goalData) => {
    return api.createGoal(goalData);
  },

  getGoalProgress: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/goals/progress`, { headers: getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Offline goal progress fallback:", e);
    }
    return null;
  },

  updateGoal: async (goalId, goalData) => {
    const res = await safeFetch(`${API_BASE}/goals/${goalId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(goalData)
    });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to update goal");
      throw new Error(msg);
    }
    return res.json();
  },

  recordWeight: async (weightKg, recordedAt = null) => {
    const res = await safeFetch(`${API_BASE}/weight`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        weight_kg: Number(weightKg),
        recorded_at: recordedAt || new Date().toISOString()
      })
    });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to log weight");
      throw new Error(msg);
    }
    return res.json();
  },

  getWeightHistory: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/weight/history`, { headers: getAuthHeaders() });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("Could not fetch weight history:", e);
    }
    return [];
  },

  getNutritionTargets: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/nutrition/targets`, { headers: getAuthHeaders() });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Offline targets calculation");
    }
    const prof = await db.profile.toCollection().first();
    return {
      target_calories: prof?.calorie_target || 2000,
      protein_g: prof?.protein_target_g || 110,
      carbs_g: 240,
      fat_g: 60,
      fiber_g: 28,
      water_ml: 2500
    };
  },


  getAllergies: async () => {
    const res = await safeFetch(`${API_BASE}/allergies`, { headers: getAuthHeaders() });
    if (!res.ok) return [];
    return res.json();
  },

  createAllergy: async (data) => {
    const res = await safeFetch(`${API_BASE}/allergies`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to record allergy");
      throw new Error(msg);
    }
    return res.json();
  },

  deleteAllergy: async (allergyId) => {
    const res = await safeFetch(`${API_BASE}/allergies/${allergyId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to delete allergy");
      throw new Error(msg);
    }
    return res.json();
  },

  // Foods (Offline First with IndexedDB caching)
  searchFoods: async (query = '', category = '') => {
    try {
      const params = new URLSearchParams();
      if (query) params.append('query', query);
      if (category) params.append('category', category);
      const res = await safeFetch(`${API_BASE}/foods?${params.toString()}`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          await db.foods.bulkPut(data);
        }
        return data;
      }
    } catch (e) {
      console.warn("Offline food search fallback");
    }

    const q = query.trim().toLowerCase();
    const offlineList = await db.foods.filter(f => {
      const nameMatch = !q || (f.name && f.name.toLowerCase().includes(q));
      const catMatch = !category || (f.category && f.category.toLowerCase() === category.toLowerCase());
      return nameMatch && catMatch;
    }).toArray();

    if (!q) return offlineList;

    return offlineList.sort((a, b) => {
      const aName = (a.name || '').toLowerCase();
      const bName = (b.name || '').toLowerCase();
      const aMain = aName.split('(')[0].trim();
      const bMain = bName.split('(')[0].trim();

      const getScore = (name, main) => {
        if (name === q) return 0;
        if (main === q) return 1;
        if (main.startsWith(q)) return 2;
        if (new RegExp(`\\b${q}\\b`, 'i').test(main)) return 3;
        if (main.includes(q)) return 4;
        if (name.includes(q)) return 5;
        return 6;
      };

      const scoreA = getScore(aName, aMain);
      const scoreB = getScore(bName, bMain);
      if (scoreA !== scoreB) return scoreA - scoreB;
      return aName.length - bName.length;
    });
  },

  getFoodByBarcode: async (barcode) => {
    const res = await safeFetch(`${API_BASE}/foods/barcode/${barcode}`, { headers: getAuthHeaders() });
    if (!res.ok) {
      const msg = await parseError(res, "Food not found for this barcode");
      throw new Error(msg);
    }
    return res.json();
  },

  getRecentFoods: async (limit = 20) => {
    try {
      const res = await safeFetch(`${API_BASE}/foods/recent?limit=${limit}`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        return Array.isArray(data) ? data : [];
      }
    } catch (e) {
      console.warn("Offline recent foods fallback:", e);
    }
    return [];
  },

  getFavoriteFoods: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/foods/favorites`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        return Array.isArray(data) ? data : [];
      }
    } catch (e) {
      console.warn("Offline favorite foods fallback:", e);
    }
    return [];
  },

  addFavoriteFood: async (foodId) => {
    const res = await safeFetch(`${API_BASE}/foods/${foodId}/favorite`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to add favorite");
      throw new Error(msg);
    }
    return res.json();
  },

  removeFavoriteFood: async (foodId) => {
    const res = await safeFetch(`${API_BASE}/foods/${foodId}/favorite`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to remove favorite");
      throw new Error(msg);
    }
    return res.json();
  },

  toggleFavoriteFood: async (foodId, isFavorite) => {
    if (isFavorite) {
      return api.removeFavoriteFood(foodId);
    } else {
      return api.addFavoriteFood(foodId);
    }
  },

  // Meals (Offline First with IndexedDB and Sync Status)
  getMeals: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/meals`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          const tagged = data.map(m => normalizeMeal({
            ...m,
            date: m.date || (m.occurred_at || '').split('T')[0],
            sync_status: 'synced'
          }));
          await db.meals.bulkPut(tagged);
          return tagged;
        }
      }
    } catch (e) {
      console.warn("Offline meals cache fallback");
    }
    const all = await db.meals.toArray();
    return all.map(normalizeMeal);
  },

  getTodayMeals: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/meals/today`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          const tagged = data.map(m => normalizeMeal({
            ...m,
            date: m.date || getLocalDateFromTimestamp(m.occurred_at),
            sync_status: 'synced'
          }));
          await db.meals.bulkPut(tagged);
          return tagged;
        }
      }
    } catch (e) {
      console.warn("Offline today meals cache fallback");
    }
    const todayStr = getToday();
    const all = await db.meals.toArray();
    return all
      .filter(m => (m.date === todayStr || getLocalDateFromTimestamp(m.occurred_at) === todayStr))
      .map(normalizeMeal);
  },

  getMealHistory: async (dateStr = null) => {
    const targetDate = dateStr || getToday();
    try {
      const url = `${API_BASE}/meals/history?date=${encodeURIComponent(targetDate)}`;
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        return {
          ...data,
          meals: (data.meals || []).map(normalizeMeal)
        };
      }
    } catch (e) {
      console.warn("Failed to fetch meal history from backend:", e);
    }
    // Offline fallback for history
    const all = await db.meals.toArray();
    const dayMeals = all
      .filter(m => (m.date === targetDate || getLocalDateFromTimestamp(m.occurred_at) === targetDate))
      .map(normalizeMeal);

    let cal = 0, pro = 0, carb = 0, fat = 0, fib = 0;
    dayMeals.forEach(m => {
      (m.items || []).forEach(i => {
        cal += (i.calories || 0);
        pro += (i.protein_g || i.protein || 0);
        carb += (i.carbs_g || i.carbs || 0);
        fat += (i.fat_g || i.fat || 0);
        fib += (i.fiber_g || i.fiber || 0);
      });
    });
    return {
      date: targetDate,
      display_date: formatDate(targetDate, 'full'),
      is_today: targetDate === getToday(),
      is_future: targetDate > getToday(),
      has_data: dayMeals.length > 0,
      total_calories: Math.round(cal),
      total_protein: Math.round(pro * 10) / 10,
      total_carbs: Math.round(carb * 10) / 10,
      total_fat: Math.round(fat * 10) / 10,
      total_fiber: Math.round(fib * 10) / 10,
      target_calories: 2000,
      target_protein: 100,
      target_carbs: 250,
      target_fat: 60,
      target_fiber: 28,
      water_ml: 0,
      water_target_ml: 2500,
      exercise_calories: 0,
      meal_count: dayMeals.length,
      meals: dayMeals
    };
  },

  getMealHistoryRange: async (startDate, endDate) => {
    try {
      const res = await safeFetch(`${API_BASE}/meals/history/range?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("Failed to fetch meal history range:", e);
    }
    return { start_date: startDate, end_date: endDate, days: [], total_meals: 0 };
  },

  createMeal: async (mealData) => {
    const clientTs = mealData.occurred_at || new Date().toISOString();
    const mealDate = mealData.date || getLocalDateFromTimestamp(clientTs);
    let result = null;

    try {
      const res = await safeFetch(`${API_BASE}/meals`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(mealData)
      });
      if (res.ok) {
        result = await res.json();
        const norm = normalizeMeal(result);
        norm.sync_status = 'synced';
        norm.date = getLocalDateFromTimestamp(norm.occurred_at || clientTs);
        await db.meals.put(norm);
        return norm;
      }
    } catch (e) {
      console.warn("Backend offline during meal creation; saving offline with pending_sync status");
    }

    const tempId = 'offline_meal_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    const rawLocal = {
      ...mealData,
      id: tempId,
      occurred_at: clientTs,
      date: mealDate,
      sync_status: 'pending_sync'
    };
    result = normalizeMeal(rawLocal);
    await db.meals.put(result);
    await enqueueOfflineAction('meal', tempId, 'INSERT', mealData);
    return result;
  },

  updateMeal: async (mealId, updateData) => {
    try {
      const res = await safeFetch(`${API_BASE}/meals/${mealId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(updateData)
      });
      if (res.ok) {
        const updated = await res.json();
        const norm = normalizeMeal(updated);
        norm.sync_status = 'synced';
        await db.meals.put(norm);
        return norm;
      }
    } catch (e) {
      console.warn("Failed to update meal online, updating local cache:", e);
    }
    const existing = await db.meals.get(mealId);
    if (existing) {
      const merged = normalizeMeal({ ...existing, ...updateData, sync_status: 'pending' });
      await db.meals.put(merged);
      await enqueueOfflineAction('meal', mealId, 'UPDATE', updateData);
      return merged;
    }
    return null;
  },

  deleteMeal: async (mealId) => {
    try {
      await safeFetch(`${API_BASE}/meals/${mealId}`, { method: 'DELETE', headers: getAuthHeaders() });
    } catch (e) {
      await enqueueOfflineAction('meal', mealId, 'DELETE', { id: mealId });
    }
    await db.meals.delete(mealId);
    return true;
  },


  // Tracking: Water
  addWater: async (amount, dateStr = null) => {
    return api.logWater(typeof amount === 'object' ? amount : { amount_ml: amount, date: dateStr });
  },

  logWater: async (data) => {
    const amount = typeof data === 'object' ? parseFloat(data.amount_ml || data.amount || 250) : parseFloat(data || 250);
    const dateStr = (typeof data === 'object' && data.date) ? data.date : new Date().toISOString().split('T')[0];
    const now = new Date();
    const timeStr = (typeof data === 'object' && data.time) ? data.time : `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    const logId = 'w_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);

    const payload = {
      amount_ml: amount,
      date: dateStr,
      time: timeStr,
      recorded_at: (typeof data === 'object' && data.recorded_at) ? data.recorded_at : `${dateStr}T${timeStr}:00Z`
    };

    const localEntry = {
      id: logId,
      ...payload,
      sync_status: 'pending'
    };

    try {
      const res = await safeFetch(`${API_BASE}/water`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const saved = await res.json();
        localEntry.id = saved.id || logId;
        localEntry.sync_status = 'synced';
        localEntry.recorded_at = saved.recorded_at || localEntry.recorded_at;
        await db.water_logs.put(localEntry);
        return saved;
      }
    } catch (e) {
      await enqueueOfflineAction('water', logId, 'INSERT', payload);
    }

    await db.water_logs.put(localEntry);
    return localEntry;
  },

  getWaterLogs: async (dateStr = null) => {
    try {
      const url = dateStr ? `${API_BASE}/water?date=${dateStr}` : `${API_BASE}/water`;
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          await db.water_logs.bulkPut(data.map(d => ({ ...d, sync_status: 'synced', date: (d.recorded_at || '').split('T')[0] })));
        }
        return data;
      }
    } catch (e) {
      console.warn("Offline water logs fetch fallback:", e);
    }
    const all = await db.water_logs.toArray();
    if (!dateStr) return all;
    return all.filter(w => (w.recorded_at || w.date || '').startsWith(dateStr));
  },

  getWaterSummary: async (dateStr = null) => {
    const targetDateStr = dateStr || new Date().toISOString().split('T')[0];
    try {
      const res = await safeFetch(`${API_BASE}/water/today?date=${targetDateStr}`, { headers: getAuthHeaders() });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("Offline water summary fallback:", e);
    }

    const [logs, targetData, prof] = await Promise.all([
      db.water_logs.toArray(),
      api.getNutritionTargets().catch(() => ({})),
      db.profile.toCollection().first()
    ]);
    const filtered = logs.filter(w => (w.recorded_at || w.date || '').startsWith(targetDateStr));
    const consumed = filtered.reduce((acc, w) => acc + (parseFloat(w.amount_ml) || 0), 0);
    const weightKg = prof?.weight_kg || 70.0;
    const target = targetData?.water_ml || Math.round(weightKg * 35.0) || 2500;
    const remaining = Math.max(0, target - consumed);
    const pct = target > 0 ? Math.round((consumed / target) * 100) : 0;

    return {
      date: targetDateStr,
      consumed_ml: consumed,
      target_ml: target,
      remaining_ml: remaining,
      completion_percentage: pct,
      logs: filtered
    };
  },

  deleteWater: async (waterId) => {
    try {
      const res = await safeFetch(`${API_BASE}/water/${waterId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (res.ok) {
        await db.water_logs.delete(waterId);
        return true;
      }
    } catch (e) {
      await enqueueOfflineAction('water', waterId, 'DELETE', { id: waterId });
    }
    await db.water_logs.delete(waterId);
    return true;
  },

  flushSyncQueue: async () => {
    const queue = await db.sync_queue.toArray();
    if (!queue || queue.length === 0) return { processed_count: 0 };

    const changes = queue.map(item => ({
      entity_type: item.entity_type,
      entity_id: item.entity_id,
      operation: item.operation,
      payload: item.payload || {},
      client_timestamp: item.client_timestamp || new Date().toISOString()
    }));

    try {
      const res = await safeFetch(`${API_BASE}/sync`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          device_id: 'pwa_' + (localStorage.getItem('nutriq_device_id') || 'local'),
          changes: changes
        })
      });
      if (res.ok) {
        await db.sync_queue.clear();
        return await res.json();
      }
    } catch (e) {
      console.warn("Failed to flush offline sync queue:", e);
    }
    return { processed_count: 0 };
  },

  getActivities: async (dateStr = null) => {
    try {
      const url = dateStr ? `${API_BASE}/activities?date=${encodeURIComponent(dateStr)}` : `${API_BASE}/activities`;
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          await db.exercise_logs.bulkPut(data.map(d => ({ ...d, sync_status: 'synced', date: getLocalDateFromTimestamp(d.recorded_at) })));
        }
        return data;
      }
    } catch (e) {
      console.warn("Offline activity fetch fallback:", e);
    }
    const all = await db.exercise_logs.toArray();
    if (!dateStr) return all;
    return all.filter(e => (e.date === dateStr || getLocalDateFromTimestamp(e.recorded_at) === dateStr));
  },

  getTodayActivities: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/activity/today`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          const tagged = data.map(d => ({
            ...d,
            date: getLocalDateFromTimestamp(d.recorded_at),
            sync_status: 'synced'
          }));
          await db.exercise_logs.bulkPut(tagged);
          return tagged;
        }
      }
    } catch (e) {
      console.warn("Offline today activities fallback:", e);
    }
    const todayStr = getToday();
    const all = await db.exercise_logs.toArray();
    return all.filter(e => (e.date === todayStr || getLocalDateFromTimestamp(e.recorded_at) === todayStr));
  },

  getActivityHistory: async (dateStr = null) => {
    const targetDate = dateStr || getToday();
    try {
      const url = `${API_BASE}/activity/history?date=${encodeURIComponent(targetDate)}`;
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("Failed to fetch activity history from backend:", e);
    }
    // Offline fallback for activity history
    const all = await db.exercise_logs.toArray();
    const dayActs = all.filter(e => (e.date === targetDate || getLocalDateFromTimestamp(e.recorded_at) === targetDate));
    const totalCal = dayActs.reduce((acc, a) => acc + (a.calories_burned || a.calories_burned_est || 0), 0);
    const totalDur = dayActs.reduce((acc, a) => acc + (a.duration_minutes || a.duration_min || 0), 0);
    const totalSteps = dayActs.reduce((acc, a) => acc + (a.steps || 0), 0);
    const totalDist = dayActs.reduce((acc, a) => acc + (a.distance_km || 0), 0);
    return {
      date: targetDate,
      display_date: formatDate(targetDate, 'full'),
      is_today: targetDate === getToday(),
      is_future: targetDate > getToday(),
      has_data: dayActs.length > 0,
      total_calories_burned: Math.round(totalCal * 10) / 10,
      total_duration_minutes: totalDur,
      total_steps: totalSteps,
      total_distance_km: Math.round(totalDist * 100) / 100,
      activity_count: dayActs.length,
      activities: dayActs
    };
  },

  getExercise: async (dateStr = null) => {
    return api.getActivities(dateStr);
  },

  logActivity: async (data) => {
    const logId = 'ex_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6);
    const actType = data.activity_type || data.type || 'walking';
    const duration = parseInt(data.duration_minutes || data.duration_min || 30);
    const intensity = data.intensity || 'moderate';
    const caloriesBurned = data.calories_burned !== undefined && data.calories_burned !== null && data.calories_burned > 0
      ? parseFloat(data.calories_burned)
      : (data.calories_burned_est !== undefined && data.calories_burned_est !== null && data.calories_burned_est > 0
          ? parseFloat(data.calories_burned_est)
          : null);

    const dateStr = data.date || getToday();
    const payload = {
      type: actType,
      activity_type: actType,
      activity_name: data.activity_name || (data.activity_type ? String(data.activity_type).replace(/_/g, ' ') : 'Workout'),
      duration_min: duration,
      duration_minutes: duration,
      intensity: intensity,
      calories_burned_est: caloriesBurned,
      calories_burned: caloriesBurned,
      steps: data.steps ? parseInt(data.steps) : 0,
      distance_km: data.distance_km ? parseFloat(data.distance_km) : 0.0,
      notes: data.notes || '',
      date: dateStr,
      time: data.time || '',
      ...(data.recorded_at ? { recorded_at: data.recorded_at } : {})
    };

    const localEntry = {
      id: logId,
      ...payload,
      calories_burned_est: caloriesBurned || 0,
      calories_burned: caloriesBurned || 0,
      date: dateStr,
      sync_status: 'pending'
    };

    try {
      const res = await safeFetch(`${API_BASE}/activities`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const saved = await res.json();
        localEntry.id = saved.id || logId;
        localEntry.sync_status = 'synced';
        localEntry.calories_burned_est = saved.calories_burned_est;
        localEntry.calories_burned = saved.calories_burned;
        localEntry.date = getLocalDateFromTimestamp(saved.recorded_at) || dateStr;
        await db.exercise_logs.put(localEntry);
        return saved;
      }
    } catch (e) {
      await enqueueOfflineAction('exercise', logId, 'INSERT', payload);
    }

    await db.exercise_logs.put(localEntry);
    return localEntry;
  },

  logExercise: async (data) => {
    return api.logActivity(data);
  },

  updateActivity: async (activityId, data) => {
    try {
      const res = await safeFetch(`${API_BASE}/activities/${activityId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data)
      });
      if (res.ok) {
        const saved = await res.json();
        saved.date = getLocalDateFromTimestamp(saved.recorded_at) || data.date;
        await db.exercise_logs.put({ ...saved, sync_status: 'synced' });
        return saved;
      }
    } catch (e) {
      await enqueueOfflineAction('exercise', activityId, 'UPDATE', data);
    }
    const existing = await db.exercise_logs.get(activityId);
    if (existing) {
      const updated = { ...existing, ...data, sync_status: 'pending' };
      await db.exercise_logs.put(updated);
      return updated;
    }
    return { id: activityId, ...data };
  },

  deleteActivity: async (activityId) => {
    try {
      const res = await safeFetch(`${API_BASE}/activities/${activityId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (res.ok) {
        await db.exercise_logs.delete(activityId);
        return { success: true };
      }
    } catch (e) {
      await enqueueOfflineAction('exercise', activityId, 'DELETE', {});
    }
    await db.exercise_logs.delete(activityId);
    return { success: true };
  },

  deleteExercise: async (exerciseId) => {
    return api.deleteActivity(exerciseId);
  },

  logWeight: async (weightKg) => {
    const logId = 'wt_' + Date.now();
    try {
      const res = await safeFetch(`${API_BASE}/weight`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ weight_kg: weightKg })
      });
      if (res.ok) return res.json();
    } catch (e) {
      await enqueueOfflineAction('weight', logId, 'INSERT', { weight_kg: weightKg });
    }
    return { weight_kg: weightKg, id: logId, recorded_at: new Date().toISOString() };
  },

  // Daily Summary (Offline + Online)
  getDailySummary: async (dateStr = null) => {
    const targetDateStr = dateStr || new Date().toISOString().split('T')[0];
    try {
      const url = `${API_BASE}/daily-summary?date=${targetDateStr}`;
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        await db.daily_summaries.put({ date: targetDateStr, ...data, updated_at: new Date().toISOString() });
        return data;
      }
    } catch (e) {
      console.warn("Backend offline, calculating daily summary from local IndexedDB:", e);
    }

    const [allMeals, waterLogs, exerciseLogs, profileData, targetData] = await Promise.all([
      db.meals.toArray(),
      db.water_logs.toArray(),
      db.exercise_logs.toArray(),
      db.profile.toCollection().first(),
      api.getNutritionTargets().catch(() => null)
    ]);

    return calculateLocalDailySummary(allMeals, waterLogs, profileData, targetData, targetDateStr, exerciseLogs);
  },

  // Weekly Summary (Offline + Online)
  getWeeklySummary: async (weekStartStr = null) => {
    try {
      const url = weekStartStr ? `${API_BASE}/weekly-summary?week_start=${weekStartStr}` : `${API_BASE}/weekly-summary`;
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        await db.weekly_summaries.put({ week_start: data.week_start, ...data, updated_at: new Date().toISOString() });
        return data;
      }
    } catch (e) {
      console.warn("Backend offline, calculating weekly summary from local IndexedDB:", e);
    }

    const [allMeals, waterLogs, exerciseLogs, profileData, targetData] = await Promise.all([
      db.meals.toArray(),
      db.water_logs.toArray(),
      db.exercise_logs.toArray(),
      db.profile.toCollection().first(),
      api.getNutritionTargets().catch(() => null)
    ]);

    return calculateLocalWeeklySummary(allMeals, waterLogs, profileData, targetData, weekStartStr, exerciseLogs);
  },

  // Dynamic Grounded Nutrition Insights API
  getNutritionInsights: async (dateStr = null) => {
    const targetDateStr = dateStr || new Date().toISOString().split('T')[0];
    try {
      const url = `${API_BASE}/nutrition/insights?date=${targetDateStr}`;
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("Backend offline, generating fallback insights:", e);
    }
    const summary = await api.getDailySummary(targetDateStr);
    return {
      date: targetDateStr,
      has_data: summary?.has_data || false,
      goal: summary?.goal_display || "Weight Loss",
      summary: summary?.has_data ? `You've logged ${summary?.calories?.consumed || 0} kcal today.` : "Log your first meal to see dynamic insights.",
      insights: summary?.has_data ? [
        {
          id: "daily_cal",
          type: "info",
          variant: "cyan",
          title: "Calorie Budget",
          message: `You have consumed ${summary?.calories?.consumed || 0} of ${summary?.calories?.target || 2000} kcal (${summary?.calories?.remaining || 0} kcal remaining).`,
          metric: `${summary?.calories?.remaining || 0} kcal left`,
          icon: "flame"
        }
      ] : []
    };
  },

  // Smart Nutrition Status & Food Recommendations (Offline + Online)
  getNutritionStatus: async (dateStr = null, mealType = null) => {
    const targetDateStr = dateStr || new Date().toISOString().split('T')[0];
    try {
      const params = new URLSearchParams();
      if (dateStr) params.append('date', targetDateStr);
      if (mealType) params.append('meal_type', mealType);
      const url = `${API_BASE}/nutrition/status?${params.toString()}`;
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("Backend offline, evaluating nutrition status from IndexedDB:", e);
    }
    return evaluateOfflineNutritionStatus(targetDateStr, mealType);
  },

  // ML-Powered Smart Recommendations Endpoint
  getSmartRecommendations: async (dateStr = null, mealType = null, limit = 4) => {
    const targetDateStr = dateStr || new Date().toISOString().split('T')[0];
    try {
      const params = new URLSearchParams();
      if (dateStr) params.append('date', targetDateStr);
      if (mealType) params.append('meal_type', mealType);
      params.append('limit', String(limit));
      const url = `${API_BASE}/recommendations?${params.toString()}`;
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("Backend offline, generating smart recommendations locally:", e);
    }
    return calculateLocalSmartRecommendations(targetDateStr, mealType, limit);
  },

  // AI Endpoints
  analyzeFoodText: async (text, mealType = 'breakfast') => {
    const res = await safeFetch(`${API_BASE}/ai/analyze-food`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ text, meal_type: mealType })
    });
    if (!res.ok) {
      const msg = await parseError(res, "AI analysis failed");
      throw new Error(msg);
    }
    return res.json();
  },

  getRecommendations: async () => {
    const res = await safeFetch(`${API_BASE}/ai/recommend`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    if (!res.ok) return [];
    return res.json();
  },

  getActiveMealPlan: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/ai/meal-plan`, { headers: getAuthHeaders() });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Unable to fetch active meal plan:", e);
    }
    return null;
  },

  generateMealPlan: async (days = 7, budgetLevel = 'medium', options = {}) => {
    const payload = {
      days,
      budget_level: budgetLevel,
      mode: options.mode || 'generate',
      previous_plan_id: options.previousPlanId || null,
      exclude_food_ids: options.excludeFoodIds || null,
      regeneration_id: options.regenerationId || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : 'regen_' + Date.now())
    };
    const res = await safeFetch(`${API_BASE}/ai/meal-plan`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const msg = await parseError(res, "Unable to generate your meal plan right now. Please try again.");
      throw new Error(msg);
    }
    return res.json();
  },

  chatWithAssistant: async (messages) => {
    const res = await safeFetch(`${API_BASE}/ai/chat`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ messages, include_today_context: true })
    });
    if (!res.ok) {
      const msg = await parseError(res, "AI Assistant unavailable");
      throw new Error(msg);
    }
    return res.json();
  },

  analyzeFoodImage: async (imageBase64) => {
    const res = await safeFetch(`${API_BASE}/ai/analyze-image`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ image_base64: imageBase64, meal_type: 'lunch' })
    });
    if (!res.ok) {
      const msg = await parseError(res, "Image analysis failed");
      throw new Error(msg);
    }
    return res.json();
  },

  // Reminder Settings & Actions
  getReminderSettings: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/reminders/settings`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        await db.reminder_settings.put({ id: 'primary', ...data, updated_at: new Date().toISOString() });
        return data;
      }
    } catch (e) {
      console.warn("Offline reminder settings fallback");
    }
    const cached = await db.reminder_settings.get('primary');
    return cached || {
      breakfast_enabled: true,
      breakfast_time: "08:30",
      lunch_enabled: true,
      lunch_time: "13:00",
      dinner_enabled: true,
      dinner_time: "20:00",
      auto_remind_unlogged: true,
      daily_summary_time: "21:30"
    };
  },

  updateReminderSettings: async (settingsData) => {
    try {
      const res = await safeFetch(`${API_BASE}/reminders/settings`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(settingsData)
      });
      if (res.ok) {
        const data = await res.json();
        await db.reminder_settings.put({ id: 'primary', ...data, updated_at: new Date().toISOString() });
        return data;
      }
    } catch (e) {
      console.warn("Offline update reminder settings");
    }
    await db.reminder_settings.put({ id: 'primary', ...settingsData, updated_at: new Date().toISOString() });
    return settingsData;
  },

  getPendingReminders: async (currentTimeIso = null) => {
    try {
      const url = currentTimeIso
        ? `${API_BASE}/reminders/pending?current_time=${encodeURIComponent(currentTimeIso)}`
        : `${API_BASE}/reminders/pending`;
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Offline reminder check");
    }

    // Local offline reminder check using IndexedDB
    const todayDate = new Date().toISOString().split('T')[0];
    const meals = await db.meals.filter(m => (m.occurred_at || m.date || '').split('T')[0] === todayDate).toArray();
    const bLogged = meals.some(m => (m.meal_type || '').toLowerCase().includes('breakfast'));
    const lLogged = meals.some(m => (m.meal_type || '').toLowerCase().includes('lunch'));
    const dLogged = meals.some(m => (m.meal_type || '').toLowerCase().includes('dinner'));

    const now = new Date();
    const hour = now.getHours();
    let pendingSlot = null;
    if (hour >= 8 && hour < 11 && !bLogged) pendingSlot = 'breakfast';
    else if (hour >= 13 && hour < 16 && !lLogged) pendingSlot = 'lunch';
    else if (hour >= 20 && hour < 23 && !dLogged) pendingSlot = 'dinner';

    return {
      has_pending: Boolean(pendingSlot),
      slot: pendingSlot,
      reminder_title: pendingSlot ? `Time to log your ${pendingSlot}!` : null,
      reminder_body: pendingSlot ? `You haven't logged ${pendingSlot} today yet. Tap to add your meal.` : null
    };
  },

  respondToReminder: async (mealType, action, dateStr = null) => {
    try {
      const res = await safeFetch(`${API_BASE}/reminders/respond`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ meal_type: mealType, action, date: dateStr })
      });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Offline reminder response");
    }
    return { status: "success", action_recorded: action };
  },

  // Analytics
  getDailyAnalytics: async (dateStr = null) => {
    const url = dateStr ? `${API_BASE}/analytics/daily?date_str=${dateStr}` : `${API_BASE}/analytics/daily`;
    try {
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Offline daily analytics fallback");
    }
    const summary = await api.getDailySummary(dateStr);
    return {
      date: summary.date,
      consumed: {
        calories: summary.calories.consumed,
        protein_g: summary.macros.protein.consumed,
        carbs_g: summary.macros.carbohydrates.consumed,
        fat_g: summary.macros.fat.consumed,
        water_ml: summary.hydration.consumed_ml,
        burned_calories: 0.0
      },
      targets: {
        target_calories: summary.calories.target,
        protein_g: summary.macros.protein.target,
        water_ml: summary.hydration.target_ml
      },
      warnings: []
    };
  },

  getAnalytics: async (rangeKey = '7d', startDateStr = null, endDateStr = null) => {
    try {
      const params = new URLSearchParams();
      if (rangeKey) params.append('range', rangeKey);
      if (startDateStr) params.append('start_date', startDateStr);
      if (endDateStr) params.append('end_date', endDateStr);

      const url = `${API_BASE}/analytics?${params.toString()}`;
      const res = await safeFetch(url, { headers: getAuthHeaders() });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn("Analytics API request failed; attempting fallback:", e);
    }
    // Offline analytics fallback calculation
    const daysCount = rangeKey === '90d' ? 90 : (rangeKey === '30d' ? 30 : 7);
    const targetObj = await api.getNutritionTargets().catch(() => ({}));
    const calTarget = targetObj.target_calories || 2000;
    const proTarget = targetObj.protein_g || 110;
    const waterTargetL = (targetObj.water_ml || 2500) / 1000.0;

    const allMeals = await db.meals.toArray();
    const allWater = await db.water_logs.toArray();
    const allActs = await db.exercise_logs.toArray();
    const allWeights = await db.weight_logs.toArray();

    const calSeries = [];
    const waterSeries = [];
    const macroSeries = [];
    const proSeries = [];
    const actSeries = [];
    const balSeries = [];

    const todayDate = new Date();
    let totalCal = 0, totalPro = 0, totalCarb = 0, totalFat = 0, totalFib = 0, totalWaterMl = 0, totalBurned = 0, totalActiveMins = 0;
    let trackedDays = 0, waterDaysMet = 0;

    for (let i = daysCount - 1; i >= 0; i--) {
      const d = new Date(todayDate);
      d.setDate(d.getDate() - i);
      const iso = d.toISOString().split('T')[0];
      const display = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

      const dayMeals = allMeals.filter(m => (m.date === iso || (m.occurred_at && m.occurred_at.startsWith(iso))));
      const dayWater = allWater.filter(w => (w.date === iso || (w.recorded_at && w.recorded_at.startsWith(iso))));
      const dayActs = allActs.filter(a => (a.date === iso || (a.recorded_at && a.recorded_at.startsWith(iso))));

      let dCal = 0, dPro = 0, dCarb = 0, dFat = 0, dFib = 0;
      dayMeals.forEach(m => {
        (m.items || []).forEach(it => {
          dCal += (Number(it.calories) || 0);
          dPro += (Number(it.protein_g || it.protein) || 0);
          dCarb += (Number(it.carbs_g || it.carbs) || 0);
          dFat += (Number(it.fat_g || it.fat) || 0);
          dFib += (Number(it.fiber_g || it.fiber) || 0);
        });
      });

      const dWaterMl = dayWater.reduce((acc, w) => acc + (Number(w.amount_ml || w.amount) || 0), 0);
      const dWaterL = Math.round((dWaterMl / 1000) * 10) / 10;
      const dBurned = dayActs.reduce((acc, a) => acc + (Number(a.calories_burned || a.calories_burned_est) || 0), 0);
      const dMins = dayActs.reduce((acc, a) => acc + (Number(a.duration_minutes || a.duration_min) || 0), 0);

      const isTracked = dayMeals.length > 0;
      if (isTracked) {
        trackedDays++;
        totalCal += dCal;
        totalPro += dPro;
        totalCarb += dCarb;
        totalFat += dFat;
        totalFib += dFib;
      }
      if (dayWater.length > 0) {
        totalWaterMl += dWaterMl;
        if (dWaterL >= waterTargetL) waterDaysMet++;
      }
      if (dayActs.length > 0) {
        totalBurned += dBurned;
        totalActiveMins += dMins;
      }

      calSeries.push({
        date: iso,
        display_date: display,
        consumed: Math.round(dCal),
        target: calTarget,
        diff: Math.round(dCal - calTarget),
        status: !isTracked ? 'unlogged' : (dCal > calTarget * 1.15 ? 'over' : (dCal < calTarget * 0.85 ? 'under' : 'target')),
        is_tracked: isTracked
      });

      waterSeries.push({
        date: iso,
        display_date: display,
        consumed_liters: dWaterL,
        consumed_ml: dWaterMl,
        target_liters: waterTargetL,
        target_ml: targetObj.water_ml || 2500,
        goal_achieved: dWaterL >= waterTargetL && dayWater.length > 0,
        is_tracked: dayWater.length > 0
      });

      macroSeries.push({
        date: iso,
        display_date: display,
        protein_g: Math.round(dPro * 10) / 10,
        carbs_g: Math.round(dCarb * 10) / 10,
        fat_g: Math.round(dFat * 10) / 10,
        fiber_g: Math.round(dFib * 10) / 10,
        calories: Math.round(dCal),
        is_tracked: isTracked
      });

      proSeries.push({
        date: iso,
        display_date: display,
        consumed_g: Math.round(dPro * 10) / 10,
        target_g: proTarget,
        achieved_pct: Math.round((dPro / proTarget) * 100),
        is_tracked: isTracked
      });

      actSeries.push({
        date: iso,
        display_date: display,
        calories_burned: Math.round(dBurned),
        duration_minutes: dMins,
        steps: 0,
        distance_km: 0.0,
        has_activity: dayActs.length > 0
      });

      balSeries.push({
        date: iso,
        display_date: display,
        intake: Math.round(dCal),
        burned: Math.round(dBurned),
        net: Math.round(dCal - dBurned),
        target: calTarget,
        is_tracked: isTracked || dayActs.length > 0
      });
    }

    const divisor = Math.max(1, trackedDays);
    const avgCal = trackedDays > 0 ? Math.round(totalCal / divisor) : 0;
    const avgPro = trackedDays > 0 ? Math.round((totalPro / divisor) * 10) / 10 : 0;
    const avgWaterL = Math.round(((totalWaterMl / Math.max(1, allWater.length > 0 ? daysCount : 1)) / 1000) * 10) / 10;
    const adherence = trackedDays > 0 ? Math.round((calSeries.filter(c => c.status === 'target').length / trackedDays) * 100) : 0;

    return {
      range: rangeKey,
      start_date: calSeries[0]?.date || '',
      end_date: calSeries[calSeries.length - 1]?.date || '',
      summary: {
        avg_calories: avgCal,
        prev_avg_calories: null,
        calorie_change_pct: null,
        target_calories: calTarget,
        avg_protein: avgPro,
        target_protein: proTarget,
        avg_water_liters: avgWaterL,
        target_water_liters: waterTargetL,
        goal_adherence_pct: adherence,
        total_tracked_days: trackedDays,
        total_period_days: daysCount,
        has_data: trackedDays > 0 || allWater.length > 0 || allActs.length > 0
      },
      calories: calSeries,
      calorie_insight: avgCal > 0 ? `Your average intake is ${Math.abs(avgCal - calTarget)} kcal ${avgCal >= calTarget ? 'above' : 'below'} your target.` : "Start logging meals to unlock calorie insights.",
      hydration: waterSeries,
      hydration_summary: {
        avg_liters: avgWaterL,
        target_liters: waterTargetL,
        best_day: null,
        days_goal_achieved: waterDaysMet,
        total_days: daysCount,
        insight: `Hydration goal achieved on ${waterDaysMet} of ${daysCount} days.`
      },
      macros: macroSeries,
      macro_averages: {
        avg_protein_g: avgPro,
        avg_carbs_g: trackedDays > 0 ? Math.round((totalCarb / divisor) * 10) / 10 : 0,
        avg_fat_g: trackedDays > 0 ? Math.round((totalFat / divisor) * 10) / 10 : 0,
        avg_fiber_g: trackedDays > 0 ? Math.round((totalFib / divisor) * 10) / 10 : 0,
        protein_calories_pct: 25,
        carbs_calories_pct: 50,
        fat_calories_pct: 25
      },
      protein: proSeries,
      protein_summary: {
        avg_protein: avgPro,
        target_protein: proTarget,
        achievement_pct: Math.round((avgPro / proTarget) * 100),
        days_met: proSeries.filter(p => p.consumed_g >= proTarget * 0.9).length,
        total_days: daysCount
      },
      activity: actSeries,
      activity_summary: {
        total_calories_burned: Math.round(totalBurned),
        total_duration_minutes: totalActiveMins,
        avg_calories_burned: Math.round(totalBurned / Math.max(1, daysCount)),
        total_steps: 0,
        most_active_day: null
      },
      calorie_balance: balSeries,
      weight_progress: {
        current_weight_kg: allWeights[allWeights.length - 1]?.weight_kg || targetObj.weight_kg || null,
        target_weight_kg: targetObj.target_weight_kg || null,
        starting_weight_kg: allWeights[0]?.weight_kg || null,
        weight_change_kg: 0.0,
        has_history: allWeights.length > 0,
        history: allWeights.map(w => ({
          date: (w.recorded_at || '').split('T')[0],
          display_date: (w.recorded_at || '').split('T')[0],
          weight_kg: w.weight_kg,
          recorded_at: w.recorded_at
        }))
      },
      nutrition_insights: [
        avgCal > 0 ? `Your average daily intake is ${avgCal} kcal against your ${calTarget} kcal target.` : "Log more meals to unlock daily insights.",
        `Hydration goal achieved on ${waterDaysMet} of ${daysCount} days.`
      ]
    };
  },

  getWeeklyAnalytics: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/analytics/weekly`, { headers: getAuthHeaders() });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Offline weekly analytics fallback");
    }
    const weeklySummary = await api.getWeeklySummary();
    return {
      has_data: weeklySummary.has_data,
      daily_breakdown: weeklySummary.daily_breakdown.map(d => ({
        day: d.day_name.substring(0, 3),
        date: d.date,
        calories: d.calories_consumed,
        target_calories: d.calorie_target,
        protein_g: d.protein_consumed_g,
        water_ml: d.water_consumed_ml,
        burned_calories: 0.0
      })),
      weekly_averages: {
        avg_daily_calories: weeklySummary.summary.avg_daily_calories,
        avg_daily_protein_g: weeklySummary.summary.avg_protein_g,
        total_weekly_calories: weeklySummary.summary.total_weekly_calories
      },
      weight_history: []
    };
  },

  // Sync Worker
  flushSyncQueue: async () => {
    const pending = await db.sync_queue.toArray();
    if (pending.length === 0) return { processed_count: 0, pending_count: 0 };
    const deviceId = localStorage.getItem('nutriq_device_id') || 'browser_' + Math.random().toString(36).substring(2, 9);
    localStorage.setItem('nutriq_device_id', deviceId);

    try {
      const res = await safeFetch(`${API_BASE}/sync`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          device_id: deviceId,
          changes: pending
        })
      });
      if (res.ok) {
        const data = await res.json();
        // Update all local meals to synced
        for (const p of pending) {
          if (p.entity_type === 'meal' && p.entity_id) {
            const m = await db.meals.get(p.entity_id);
            if (m) {
              m.sync_status = 'synced';
              await db.meals.put(m);
            }
          }
        }
        await db.sync_queue.clear();
        return { ...data, pending_count: 0 };
      }
    } catch (e) {
      console.warn("Sync failed (will automatically retry later):", e);
    }
    const remaining = await db.sync_queue.count();
    return { processed_count: 0, pending_count: remaining };
  },

  // Multi-Format Report Exports (Offline + Online)
  downloadDailyReport: async (dateStr, format, summaryData = null, profile = null) => {
    if (typeof navigator !== 'undefined' && navigator.onLine) {
      try {
        const res = await safeFetch(`${API_BASE}/export/${format}`, { headers: getAuthHeaders() });
        if (res.ok) {
          const blob = await res.blob();
          const filename = `NutriQ_Daily_Report_${dateStr}.${format}`;
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.style.display = 'none';
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          setTimeout(() => {
            window.URL.revokeObjectURL(url);
            a.remove();
          }, 100);
          return { success: true, filename };
        }
      } catch (e) {
        console.warn("Online export failed; falling back to offline report generator:", e);
      }
    }

    const activeSummary = summaryData || await api.getDailySummary(dateStr);
    const activeProfile = profile || await api.getProfile();
    return reportGenerator.exportDaily(activeSummary, format, activeProfile);
  },

  downloadWeeklyReport: async (weeklyData, format, profile = null) => {
    const activeProfile = profile || await api.getProfile();
    return reportGenerator.exportWeekly(weeklyData, format, activeProfile);
  },

  downloadExport: async (format) => {
    try {
      const res = await safeFetch(`${API_BASE}/export/${format}`, {
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const disposition = res.headers.get('Content-Disposition') || '';
        let filename = '';
        const match = disposition.match(/filename="?([^";]+)"?/i);
        if (match && match[1]) {
          filename = match[1];
        } else {
          const dateStr = new Date().toISOString().split('T')[0];
          if (format === 'pdf') filename = `NutriQ_Nutrition_Report_${dateStr}.pdf`;
          else if (format === 'csv') filename = `NutriQ_Nutrition_Data_${dateStr}.csv`;
          else filename = `NutriQ_Data_Backup_${dateStr}.json`;
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
          window.URL.revokeObjectURL(url);
          a.remove();
        }, 100);
        return { success: true, filename };
      }
    } catch (e) {
      console.warn("Online full export failed, generating offline snapshot:", e);
    }

    const summary = await api.getDailySummary();
    const prof = await api.getProfile();
    return reportGenerator.exportDaily(summary, format, prof);
  },

  exportUserData: async () => {
    const res = await safeFetch(`${API_BASE}/export/json`, { headers: getAuthHeaders() });
    if (!res.ok) {
      const msg = await parseError(res, "Unable to export your data right now. Please try again.");
      throw new Error(msg);
    }
    return res.json();
  },

  getConsents: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/privacy/consents`, { headers: getAuthHeaders() });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Unable to fetch consent records:", e);
    }
    return [];
  },

  deleteAccount: async () => {
    const res = await safeFetch(`${API_BASE}/privacy/account`, { method: 'DELETE', headers: getAuthHeaders() });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to delete account");
      throw new Error(msg);
    }
    localStorage.clear();
    await db.delete();
    return res.json();
  },

  // ==========================================
  // NUTRIQ DAILY STREAK API
  // ==========================================
  getStreak: async () => {
    return api.getStreakStatus();
  },

  getStreakStatus: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/streak`, { headers: getAuthHeaders() });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Failed to fetch streak status:", e);
    }
    // Calculate local fallback streak using centralized calculateCurrentStreak
    try {
      const [meals, waterLogs, exLogs] = await Promise.all([
        db.meals.toArray(),
        db.water_logs.toArray(),
        db.exercise_logs ? db.exercise_logs.toArray() : []
      ]);
      const currentUserId = typeof localStorage !== 'undefined' ? localStorage.getItem('nutriq_user_id') : null;
      const currentUserEmail = typeof localStorage !== 'undefined' ? localStorage.getItem('nutriq_email') : null;
      return calculateCurrentStreak(meals, {
        userId: currentUserId,
        email: currentUserEmail,
        additionalDates: [
          ...waterLogs.filter(w => (w.amount_ml || 0) > 0).map(w => w.recorded_at || w.date),
          ...exLogs.map(e => e.recorded_at || e.date)
        ]
      });
    } catch (err) {
      console.warn("Could not calculate local fallback streak:", err);
    }
    return {
      current_streak: 0,
      longest_streak: 0,
      total_active_days: 0,
      last_completed_date: null,
      completed_today: false,
      weekly_history: [],
      new_milestone: null,
      milestones_achieved: []
    };
  },

  checkStreakStatus: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/streak/check`, { method: 'POST', headers: getAuthHeaders() });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Failed to check streak status:", e);
    }
    return api.getStreakStatus();
  },

  getStreakHistory: async () => {
    try {
      const res = await safeFetch(`${API_BASE}/streak/history`, { headers: getAuthHeaders() });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Failed to fetch streak history:", e);
    }
    return { current_streak: 0, longest_streak: 0, total_active_days: 0, history: [] };
  },

  acknowledgeMilestone: async (milestone) => {
    try {
      const res = await safeFetch(`${API_BASE}/streak/milestone-ack`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ milestone })
      });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Failed to acknowledge milestone:", e);
    }
    return { success: true };
  },

  // ==========================================
  // PERSISTENT AI CONVERSATIONS & CHAT HISTORY
  // ==========================================
  getConversations: async (searchQuery = '') => {
    try {
      const q = searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : '';
      const res = await safeFetch(`${API_BASE}/ai/conversations${q}`, { headers: getAuthHeaders() });
      if (res.ok) return res.json();
    } catch (e) {
      console.warn("Failed to fetch conversations:", e);
    }
    return [];
  },

  getConversation: async (conversationId) => {
    const res = await safeFetch(`${API_BASE}/ai/conversations/${conversationId}`, { headers: getAuthHeaders() });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to load conversation");
      throw new Error(msg);
    }
    return res.json();
  },

  createConversation: async (title = "New Conversation") => {
    const res = await safeFetch(`${API_BASE}/ai/conversations`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ title })
    });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to create new conversation");
      throw new Error(msg);
    }
    return res.json();
  },

  renameConversation: async (conversationId, title) => {
    const res = await safeFetch(`${API_BASE}/ai/conversations/${conversationId}`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify({ title })
    });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to rename conversation");
      throw new Error(msg);
    }
    return res.json();
  },

  deleteConversation: async (conversationId) => {
    const res = await safeFetch(`${API_BASE}/ai/conversations/${conversationId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to delete conversation");
      throw new Error(msg);
    }
    return res.json();
  },

  sendConversationMessage: async ({ conversationId, content, stream = true, onChunk, onDone, onError, signal }) => {
    try {
      if (!stream) {
        const res = await safeFetch(`${API_BASE}/ai/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ content, stream: false }),
          signal
        });
        if (!res.ok) {
          const msg = await parseError(res, "Failed to send message");
          const err = new Error(msg);
          err.status = res.status;
          throw err;
        }
        return res.json();
      }

      // SSE Streaming
      const response = await safeFetch(`${API_BASE}/ai/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ content, stream: true }),
        signal
      });

      if (!response.ok) {
        const msg = await parseError(response, "Streaming request failed");
        const err = new Error(msg);
        err.status = response.status;
        throw err;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let finalMetadata = null;
      let messageId = null;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data:")) {
            try {
              const data = JSON.parse(trimmed.replace(/^data:\s*/, ""));
              if (data.chunk && onChunk) {
                onChunk(data.chunk);
              }
              if (data.done) {
                finalMetadata = data.metadata || {};
                messageId = data.message_id;
                if (onDone) onDone(finalMetadata, messageId);
              }
            } catch (e) {
              console.warn("Error parsing SSE event:", e);
            }
          }
        }
      }

      return { metadata: finalMetadata, message_id: messageId };
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error("NutriQ AI request failed:", err);
      }
      if (onError) onError(err);
      throw err;
    }
  },

  getCurrentChatSession: async () => {
    const res = await safeFetch(`${API_BASE}/ai/chat/current`, { headers: getAuthHeaders() });
    if (!res.ok) {
      const msg = await parseError(res, "Failed to load chat session");
      throw new Error(msg);
    }
    return res.json();
  },

  getChatHistory: async () => {
    return api.getConversations();
  },

  createChatSession: async (title = "New Conversation") => {
    return api.createConversation(title);
  },

  deleteChatSession: async (sessionId) => {
    return api.deleteConversation(sessionId);
  },

  sendChatMessage: async ({ content, sessionId, stream = true, onChunk, onDone, onError, signal }) => {
    if (sessionId) {
      return api.sendConversationMessage({ conversationId: sessionId, content, stream, onChunk, onDone, onError, signal });
    }
    // Fallback to /ai/chat/message
    if (!stream) {
      const res = await safeFetch(`${API_BASE}/ai/chat/message`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ content, session_id: sessionId, stream: false }),
        signal
      });
      if (!res.ok) {
        const msg = await parseError(res, "Failed to send message");
        throw new Error(msg);
      }
      return res.json();
    }

    const response = await safeFetch(`${API_BASE}/ai/chat/message`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ content, session_id: sessionId, stream: true }),
      signal
    });

    if (!response.ok) {
      const msg = await parseError(response, "Streaming request failed");
      if (onError) onError(new Error(msg));
      throw new Error(msg);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let finalMetadata = null;
    let messageId = null;

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data:")) {
            try {
              const data = JSON.parse(trimmed.replace(/^data:\s*/, ""));
              if (data.chunk && onChunk) {
                onChunk(data.chunk);
              }
              if (data.done) {
                finalMetadata = data.metadata || {};
                messageId = data.message_id;
                if (onDone) onDone(finalMetadata, messageId);
              }
            } catch (e) {
              console.warn("Error parsing SSE event:", e);
            }
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log("Streaming cancelled by user");
      } else {
        if (onError) onError(err);
        throw err;
      }
    }

    return { metadata: finalMetadata, message_id: messageId };
  },

  chatWithAssistant: async (messages) => {
    const res = await safeFetch(`${API_BASE}/ai/chat`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ messages })
    });
    if (!res.ok) {
      const msg = await parseError(res, "AI Assistant is currently unavailable.");
      throw new Error(msg);
    }
    return res.json();
  }
};

