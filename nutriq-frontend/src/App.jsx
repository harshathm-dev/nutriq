import React, { useEffect } from 'react';
import { useStore, isPublicPath, isProfileComplete, pathToTab } from './store/useStore';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { WelcomePage } from './pages/WelcomePage';
import { AuthPage } from './pages/AuthPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { DashboardPage } from './pages/DashboardPage';
import { AddFoodPage } from './pages/AddFoodPage';
import { FoodCatalogPage } from './pages/FoodCatalogPage';
import { MealPlannerPage } from './pages/MealPlannerPage';
import { AIAssistantPage } from './pages/AIAssistantPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { PrivacyPage } from './pages/PrivacyPage';
import { SettingsPage } from './pages/SettingsPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { BillingPage } from './pages/BillingPage';
import { DailySummaryPage } from './pages/DailySummaryPage';
import { WeeklySummaryPage } from './pages/WeeklySummaryPage';
import { MealHistoryPage } from './pages/MealHistoryPage';
import { ActivityHistoryPage } from './pages/ActivityHistoryPage';
import { ReminderToast } from './components/ReminderToast';
import { BottomNav } from './components/BottomNav';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Flame, Loader2 } from 'lucide-react';

export function App() {
  const {
    currentPath,
    activeTab,
    isInitializing,
    user,
    profile,
    checkAuth,
    setOnline,
    triggerSync,
    navigate
  } = useStore();

  useEffect(() => {
    // 1. Validate / restore authenticated session on startup
    checkAuth();

    // 2. Browser history popstate handler for back/forward navigation
    const handlePopState = () => {
      const path = window.location.pathname || '/';
      const currentUser = useStore.getState().user;
      const currentProfile = useStore.getState().profile;

      if (!currentUser) {
        if (!isPublicPath(path)) {
          navigate('/login', true);
        } else {
          navigate(path, true);
        }
      } else {
        const complete = isProfileComplete(currentProfile);
        if (!complete) {
          navigate('/profile-setup', true);
        } else {
          if (isPublicPath(path)) {
            navigate('/dashboard', true);
          } else {
            navigate(path, true);
          }
        }
      }
    };

    // 3. Network status listeners
    const handleOnline = () => {
      setOnline(true);
      triggerSync();
    };
    const handleOffline = () => setOnline(false);

    window.addEventListener('popstate', handlePopState);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // 1. Initializing Loading Screen (prevents flickering or early dashboard exposure)
  if (isInitializing) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-app)',
        gap: '20px'
      }}>
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '20px',
          background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 10px 25px rgba(16, 185, 129, 0.4)',
          animation: 'pulseGlow 2s infinite ease-in-out'
        }}>
          <Flame size={36} color="#ffffff" />
        </div>
        <div style={{ textAlign: 'center' }}>
          <h2 style={{ fontSize: '1.4rem', fontWeight: '800', background: 'linear-gradient(90deg, #34d399, #60a5fa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: '6px' }}>
            NutriQ
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
            <Loader2 size={16} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
            <span>Loading NutriQ...</span>
          </div>
        </div>
        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // 2. Unauthenticated User & Public Password Recovery Handling
  if (!user) {
    if (currentPath === '/login') {
      return (
        <ErrorBoundary>
          <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <AuthPage mode="login" />
          </div>
        </ErrorBoundary>
      );
    }
    if (currentPath === '/register') {
      return (
        <ErrorBoundary>
          <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <AuthPage mode="register" />
          </div>
        </ErrorBoundary>
      );
    }
    if (currentPath === '/forgot-password' || activeTab === 'forgot_password') {
      return (
        <ErrorBoundary>
          <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <ForgotPasswordPage />
          </div>
        </ErrorBoundary>
      );
    }
    if (currentPath.startsWith('/reset-password') || activeTab === 'reset_password') {
      return (
        <ErrorBoundary>
          <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <ResetPasswordPage />
          </div>
        </ErrorBoundary>
      );
    }
    if (currentPath === '/welcome' || currentPath === '/') {
      return (
        <ErrorBoundary>
          <WelcomePage />
        </ErrorBoundary>
      );
    }
    // Any other protected route accessed while logged out redirects / shows Login page
    return (
      <ErrorBoundary>
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <AuthPage mode="login" />
        </div>
      </ErrorBoundary>
    );
  }

  // 3. Authenticated User - Profile Incomplete Check
  const profileComplete = isProfileComplete(profile);
  if (!profileComplete) {
    return (
      <ErrorBoundary>
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <header className="glass-panel" style={{ margin: '16px 24px 0 24px', padding: '12px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '38px', height: '38px', borderRadius: '10px',
                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <Flame size={22} color="#ffffff" />
              </div>
              <div>
                <h2 style={{ fontSize: '1.2rem', fontWeight: '800', background: 'linear-gradient(90deg, #34d399, #60a5fa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  NutriQ
                </h2>
                <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '700' }}>
                  Profile Setup Required
                </span>
              </div>
            </div>
            <button
              onClick={() => useStore.getState().logout()}
              className="btn-secondary"
              style={{ padding: '6px 14px', fontSize: '0.8rem', color: '#f43f5e' }}
            >
              Logout
            </button>
          </header>

          <main className="main-content" style={{ maxWidth: '800px', margin: '0 auto', width: '100%' }}>
            <OnboardingPage onComplete={() => navigate('/dashboard')} />
          </main>
        </div>
      </ErrorBoundary>
    );
  }

  // 4. Authenticated User with Complete Profile - Main Application Routing
  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardPage />;
      case 'daily_summary':
        return <DailySummaryPage />;
      case 'weekly_summary':
        return <WeeklySummaryPage />;
      case 'meal_history':
        return <MealHistoryPage />;
      case 'activity_history':
        return <ActivityHistoryPage />;
      case 'add_food':
        return <AddFoodPage />;
      case 'search':
        return <FoodCatalogPage />;
      case 'planner':
        return <MealPlannerPage />;
      case 'assistant':
        return <AIAssistantPage />;
      case 'analytics':
        return <AnalyticsPage />;
      case 'privacy':
        return <PrivacyPage />;
      case 'settings':
        return <SettingsPage />;
      case 'billing':
        return <BillingPage />;
      case 'onboarding':
        return <OnboardingPage onComplete={() => navigate('/dashboard')} />;
      default:
        return <DashboardPage />;
    }
  };

  return (
    <ErrorBoundary>
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Navbar />

        <div style={{ display: 'flex', flex: 1, marginTop: '8px', width: '100%', minWidth: 0 }}>
          <Sidebar />
          
          <main className="main-content">
            <ErrorBoundary>
              {renderActivePage()}
            </ErrorBoundary>
          </main>
        </div>

        {/* Global Smart Meal Reminders & Daily Summary Toast Notification */}
        <ReminderToast />

        {/* Mobile Bottom Navigation */}
        <BottomNav />
      </div>
    </ErrorBoundary>
  );
}

export default App;
