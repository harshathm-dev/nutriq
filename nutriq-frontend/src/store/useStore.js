import { create } from 'zustand';
import { api } from '../services/api.js';
import { db, clearUserLocalData } from '../offline/db.js';

export const pathToTab = (path) => {
  const cleanPath = path.split('?')[0].replace(/\/+$/, '') || '/';
  switch (cleanPath) {
    case '/':
    case '/welcome':
      return 'welcome';
    case '/login':
      return 'login';
    case '/register':
      return 'register';
    case '/forgot-password':
      return 'forgot_password';
    case '/reset-password':
      return 'reset_password';
    case '/profile-setup':
      return 'onboarding';
    case '/dashboard':
      return 'dashboard';
    case '/daily-summary':
      return 'daily_summary';
    case '/weekly-summary':
      return 'weekly_summary';
    case '/meal-history':
      return 'meal_history';
    case '/activity-history':
      return 'activity_history';
    case '/log-meal':
    case '/add-food':
      return 'add_food';
    case '/food-catalog':
      return 'search';
    case '/meal-planner':
      return 'planner';
    case '/ai-assistant':
      return 'assistant';
    case '/analytics':
      return 'analytics';
    case '/family-profiles':
      return 'dashboard';
    case '/privacy':
      return 'privacy';
    case '/settings':
    case '/profile':
      return 'settings';
    case '/billing':
      return 'billing';
    default:
      return 'welcome';
  }
};

export const tabToPath = (tab) => {
  switch (tab) {
    case 'welcome': return '/welcome';
    case 'login': return '/login';
    case 'register': return '/register';
    case 'forgot_password': return '/forgot-password';
    case 'reset_password': return '/reset-password';
    case 'auth': return '/login';
    case 'onboarding': return '/profile-setup';
    case 'dashboard': return '/dashboard';
    case 'daily_summary': return '/daily-summary';
    case 'weekly_summary': return '/weekly-summary';
    case 'meal_history': return '/meal-history';
    case 'activity_history': return '/activity-history';
    case 'add_food': return '/log-meal';
    case 'search': return '/food-catalog';
    case 'planner': return '/meal-planner';
    case 'assistant': return '/ai-assistant';
    case 'analytics': return '/analytics';
    case 'privacy': return '/privacy';
    case 'settings': return '/settings';
    case 'billing': return '/billing';
    default: return '/welcome';
  }
};

export const isPublicPath = (path) => {
  const cleanPath = path.split('?')[0].replace(/\/+$/, '') || '/';
  return ['/', '/welcome', '/login', '/register', '/forgot-password', '/reset-password'].includes(cleanPath);
};

export const isProfileComplete = (profile) => {
  if (!profile) return false;
  const hasName = Boolean(profile.name && typeof profile.name === 'string' && profile.name.trim().length > 0);
  const hasAge = typeof profile.age === 'number' && profile.age >= 10 && profile.age <= 120;
  const hasGender = Boolean(profile.gender && typeof profile.gender === 'string' && profile.gender.trim().length > 0);
  const hasHeight = (typeof profile.height_cm === 'number' && profile.height_cm >= 50) || (typeof profile.height === 'number' && profile.height >= 50);
  const hasWeight = (typeof profile.weight_kg === 'number' && profile.weight_kg >= 20) || (typeof profile.weight === 'number' && profile.weight >= 20);
  const hasActivity = Boolean(profile.activity_level && typeof profile.activity_level === 'string' && profile.activity_level.trim().length > 0);
  const hasGoal = Boolean(profile.fitness_goal && typeof profile.fitness_goal === 'string' && profile.fitness_goal.trim().length > 0);

  return Boolean(hasName && hasAge && hasGender && hasHeight && hasWeight && hasActivity && hasGoal);
};

export const useStore = create((set, get) => ({
  currentPath: typeof window !== 'undefined' ? (window.location.pathname || '/') : '/',
  activeTab: typeof window !== 'undefined' ? pathToTab(window.location.pathname || '/') : 'welcome',
  isInitializing: true,
  user: null,
  profile: null,
  targets: {
    target_calories: 2000,
    protein_g: 110,
    carbs_g: 240,
    fat_g: 60,
    fiber_g: 28,
    water_ml: 2500,
    bmr: 1650,
    tdee: 2200
  },
  dailyAnalytics: {
    consumed: {
      calories: 0,
      protein_g: 0,
      carbs_g: 0,
      fat_g: 0,
      fiber_g: 0,
      water_ml: 0,
      burned_calories: 0,
      net_calories: 0,
      remaining_calories: 2000
    },
    warnings: [],
    meal_count: 0
  },
  dailySummary: null,
  reminderSettings: {
    reminders_enabled: true,
    breakfast_enabled: true,
    breakfast_time: '08:00',
    lunch_enabled: true,
    lunch_time: '13:00',
    snack_enabled: true,
    snack_time: '17:00',
    dinner_enabled: true,
    dinner_time: '20:00',
    grace_period_minutes: 30,
    daily_summary_enabled: true,
    daily_summary_time: '20:30',
    user_timezone: 'Asia/Kolkata'
  },
  pendingReminder: null,
  meals: [],
  isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
  syncPendingCount: 0,
  activeProfileContext: 'self',
  theme: typeof localStorage !== 'undefined' ? (localStorage.getItem('nutriq_theme') || 'dark') : 'dark',

  navigate: (path, replace = false) => {
    const cleanPath = path.split('?')[0].replace(/\/+$/, '') || '/';
    if (typeof window !== 'undefined' && window.location.pathname !== cleanPath) {
      if (replace) {
        window.history.replaceState({}, '', cleanPath);
      } else {
        window.history.pushState({}, '', cleanPath);
      }
    }
    set({
      currentPath: cleanPath,
      activeTab: pathToTab(cleanPath)
    });
  },

  setTab: (tab) => {
    const targetPath = tabToPath(tab);
    get().navigate(targetPath);
  },

  setTheme: (theme) => {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('nutriq_theme', theme);
    }
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', theme);
    }
    set({ theme });
  },

  setOnline: (status) => set({ isOnline: status }),
  setUser: (user) => set({ user }),
  setProfile: (profile) => set({ profile }),

  checkAuth: async () => {
    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('nutriq_token') : null;
    const userEmail = typeof localStorage !== 'undefined' ? localStorage.getItem('nutriq_email') : null;
    const userId = typeof localStorage !== 'undefined' ? localStorage.getItem('nutriq_user_id') : null;
    const path = typeof window !== 'undefined' ? (window.location.pathname || '/') : '/';

    if (token) {
      const currentUser = { token, email: userEmail, id: userId };
      set({ user: currentUser });

      try {
        const profileData = await api.getProfile().catch(() => null);
        if (profileData) {
          set({ profile: profileData });
        }
        await get().refreshAllData();

        // Check profile completion
        const complete = isProfileComplete(profileData);
        if (complete) {
          if (isPublicPath(path)) {
            get().navigate('/dashboard', true);
          } else {
            get().navigate(path, true);
          }
        } else {
          get().navigate('/profile-setup', true);
        }
      } catch (err) {
        console.warn("Auth validation error:", err);
        get().logout();
      }
    } else {
      set({ user: null, profile: null });
      if (!isPublicPath(path)) {
        get().navigate('/login', true);
      } else {
        get().navigate(path, true);
      }
    }

    set({ isInitializing: false });
  },

  logout: async () => {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('nutriq_token');
      localStorage.removeItem('nutriq_email');
      localStorage.removeItem('nutriq_user_id');
    }
    await clearUserLocalData();
    set({
      user: null,
      profile: null,
      meals: [],
      dailyAnalytics: {
        consumed: {
          calories: 0,
          protein_g: 0,
          carbs_g: 0,
          fat_g: 0,
          fiber_g: 0,
          water_ml: 0,
          burned_calories: 0,
          net_calories: 0,
          remaining_calories: 2000
        },
        warnings: [],
        meal_count: 0
      },
      dailySummary: null,
      targets: {
        target_calories: 2000,
        protein_g: 110,
        carbs_g: 240,
        fat_g: 60,
        fiber_g: 28,
        water_ml: 2500,
        bmr: 1650,
        tdee: 2200
      },
      pendingReminder: null,
      syncPendingCount: 0
    });
    get().navigate('/welcome', true);
  },

  setDailySummary: (summary) => set({ dailySummary: summary }),
  setPendingReminder: (reminder) => set({ pendingReminder: reminder }),

  fetchDailySummary: async (dateStr = null) => {
    try {
      const summary = await api.getDailySummary(dateStr);
      if (summary) {
        set({ dailySummary: summary });
      }
      return summary;
    } catch (e) {
      console.warn("Could not fetch daily summary:", e);
      return null;
    }
  },

  fetchReminderSettings: async () => {
    try {
      const settings = await api.getReminderSettings();
      if (settings) {
        set({ reminderSettings: settings });
      }
      return settings;
    } catch (e) {
      console.warn("Could not fetch reminder settings:", e);
      return null;
    }
  },

  updateReminderSettings: async (settingsData) => {
    try {
      const updated = await api.updateReminderSettings(settingsData);
      if (updated) {
        set({ reminderSettings: updated });
      }
      return updated;
    } catch (e) {
      console.warn("Could not update reminder settings:", e);
      throw e;
    }
  },

  refreshAllData: async () => {
    try {
      const [profileData, targetData, analyticsData, mealsData, summaryData, reminderData] = await Promise.all([
        api.getProfile().catch(() => null),
        api.getNutritionTargets().catch(() => null),
        api.getDailyAnalytics().catch(() => null),
        api.getTodayMeals().catch(() => []),
        api.getDailySummary().catch(() => null),
        api.getReminderSettings().catch(() => null)
      ]);

      if (profileData) set({ profile: profileData });
      if (targetData) set({ targets: targetData });
      if (analyticsData) set({ dailyAnalytics: analyticsData });
      if (mealsData) set({ meals: mealsData });
      if (summaryData) set({ dailySummary: summaryData });
      if (reminderData) set({ reminderSettings: reminderData });

      const pendingCount = await db.sync_queue.count();
      set({ syncPendingCount: pendingCount });
    } catch (e) {
      console.warn("Could not refresh data completely:", e);
    }
  },

  triggerSync: async () => {
    if (typeof navigator !== 'undefined' && !navigator.onLine) return;
    await api.flushSyncQueue();
    await get().refreshAllData();
  }
}));
