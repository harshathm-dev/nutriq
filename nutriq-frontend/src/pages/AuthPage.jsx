import React, { useState, useEffect, useRef } from 'react';
import { useStore, isProfileComplete } from '../store/useStore';
import { api } from '../services/api';
import { Flame, Lock, Mail, User, ArrowRight, CheckCircle2, AlertCircle, Sparkles, Eye, EyeOff } from 'lucide-react';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

export const AuthPage = ({ mode = 'login' }) => {
  const { currentPath, navigate, setUser, setProfile, refreshAllData } = useStore();

  const isRegister = currentPath === '/register' || mode === 'register';

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(true);
  const [aiConsentAccepted, setAiConsentAccepted] = useState(true);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState(null);

  const tokenClientRef = useRef(null);
  const isGsiInitializedRef = useRef(false);
  const handleCredentialResponseRef = useRef(null);

  const handleGoogleCredentialResponse = async (response) => {
    if (!response || !response.credential) {
      setError("Google sign-in was cancelled.");
      setGoogleLoading(false);
      return;
    }
    setError(null);
    setGoogleLoading(true);
    try {
      const data = await api.googleLogin({ credential: response.credential });
      await handleAuthSuccess(data);
    } catch (err) {
      setError(err.message || "Google sign-in could not be completed. Please try again.");
    } finally {
      setGoogleLoading(false);
    }
  };

  handleCredentialResponseRef.current = handleGoogleCredentialResponse;

  useEffect(() => {
    setError(null);

    // 1. Initialize Google Identity Services (GIS) if available (Only once)
    const initGIS = () => {
      if (typeof window !== 'undefined' && window.google?.accounts && GOOGLE_CLIENT_ID) {
        try {
          if (!isGsiInitializedRef.current && window.google.accounts.id) {
            // Initialize ID Token credential receiver once
            window.google.accounts.id.initialize({
              client_id: GOOGLE_CLIENT_ID,
              callback: (res) => {
                if (handleCredentialResponseRef.current) {
                  handleCredentialResponseRef.current(res);
                }
              },
              auto_select: false,
              cancel_on_tap_outside: true
            });
            isGsiInitializedRef.current = true;
          }

          // Initialize OAuth2 Token Client for Account Chooser Popup
          if (!tokenClientRef.current && window.google.accounts.oauth2) {
            tokenClientRef.current = window.google.accounts.oauth2.initTokenClient({
              client_id: GOOGLE_CLIENT_ID,
              scope: 'openid email profile',
              callback: async (tokenResponse) => {
                if (tokenResponse && tokenResponse.access_token) {
                  try {
                    setGoogleLoading(true);
                    setError(null);
                    const data = await api.googleLogin({ accessToken: tokenResponse.access_token });
                    await handleAuthSuccess(data);
                  } catch (err) {
                    setError(err.message || "Google sign-in could not be completed. Please try again.");
                  } finally {
                    setGoogleLoading(false);
                  }
                } else if (tokenResponse?.error) {
                  setGoogleLoading(false);
                  if (tokenResponse.error === 'access_denied' || tokenResponse.error === 'user_logged_out') {
                    setError("Google sign-in was cancelled.");
                  } else {
                    setError("Google sign-in could not be completed. Please try again.");
                  }
                }
              },
              error_callback: (err) => {
                setGoogleLoading(false);
                if (err.type === 'popup_closed') {
                  setError("Google sign-in was cancelled.");
                } else if (err.type === 'popup_blocked_by_browser') {
                  setError("Google sign-in popup was blocked by your browser. Please allow popups for this site or try again.");
                } else {
                  setError("Google sign-in could not be completed. Please try again.");
                }
              }
            });
          }
        } catch (e) {
          console.warn("GIS initialization notice:", e);
        }
      }
    };

    initGIS();

    // 2. Check for Google OAuth redirect callback parameters in URL
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const token = params.get('token');
      const emailParam = params.get('email');
      const userIdParam = params.get('user_id');
      const roleParam = params.get('role');
      const authError = params.get('error');

      if (token && userIdParam) {
        window.history.replaceState({}, document.title, window.location.pathname);
        handleAuthSuccess({
          access_token: token,
          email: emailParam || '',
          user_id: userIdParam,
          role: roleParam || 'user'
        });
        return;
      }

      if (authError) {
        window.history.replaceState({}, document.title, window.location.pathname);
        if (authError === 'google_cancelled' || authError === 'access_denied') {
          setError("Google sign-in was cancelled.");
        } else if (authError === 'unconfigured') {
          setError("Google sign-in is not configured on this server. Please sign in with email or configure GOOGLE_CLIENT_ID.");
        } else if (authError === 'origin_mismatch') {
          setError("Google sign-in origin mismatch. Please ensure http://localhost:5173 is added to Authorized JavaScript Origins in Google Cloud Console.");
        } else {
          setError("Google sign-in could not be completed. Please try again.");
        }
      }
    }
  }, [currentPath, mode]);

  const handleGoogleSignIn = () => {
    setError(null);
    setGoogleLoading(true);

    // 1. If GIS OAuth2 tokenClient is available, launch Account Chooser popup
    if (tokenClientRef.current) {
      try {
        tokenClientRef.current.requestAccessToken({ prompt: 'select_account' });
        return;
      } catch (err) {
        console.warn("tokenClient requestAccessToken failed, falling back to GIS prompt/redirect", err);
      }
    }

    // 2. If GIS ID Token prompt is available, launch GIS prompt
    if (typeof window !== 'undefined' && window.google?.accounts?.id && GOOGLE_CLIENT_ID) {
      try {
        window.google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            window.location.href = api.getGoogleAuthUrl();
          }
        });
        return;
      } catch (err) {
        console.warn("GIS prompt invocation failed, falling back to redirect flow", err);
      }
    }

    // 3. Fallback to direct backend OAuth redirect flow
    window.location.href = api.getGoogleAuthUrl();
  };

  const handleAuthSuccess = async (data) => {
    localStorage.setItem('nutriq_token', data.access_token);
    localStorage.setItem('nutriq_email', data.email);
    localStorage.setItem('nutriq_user_id', data.user_id);
    setUser({ token: data.access_token, email: data.email, id: data.user_id });

    const prof = await api.getProfile().catch(() => null);
    if (prof) {
      setProfile(prof);
    }
    await refreshAllData();

    navigate('/dashboard');
    setGoogleLoading(false);
  };

  const validateRegistration = () => {
    if (!name.trim()) {
      return "Name is required.";
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim() || !emailRegex.test(email.trim())) {
      return "Please provide a valid email address.";
    }
    if (!password || password.length < 6) {
      return "Password must be at least 6 characters long.";
    }
    if (password !== confirmPassword) {
      return "Password and Confirm Password do not match.";
    }
    if (!termsAccepted) {
      return "You must accept the Terms of Service to create an account.";
    }
    if (!aiConsentAccepted) {
      return "You must accept the AI & Health Data Consent to use NutriQ intelligence.";
    }
    return null;
  };

  const validateLogin = () => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim() || !emailRegex.test(email.trim())) {
      return "Please provide a valid email address.";
    }
    if (!password) {
      return "Password is required.";
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const validationError = isRegister ? validateRegistration() : validateLogin();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    try {
      if (isRegister) {
        const data = await api.register({
          name: name.trim(),
          email: email.trim().toLowerCase(),
          password,
          terms_accepted: termsAccepted,
          ai_consent_accepted: aiConsentAccepted
        });
        await handleAuthSuccess(data);
      } else {
        const data = await api.login(email.trim().toLowerCase(), password);
        await handleAuthSuccess(data);
      }
    } catch (err) {
      setError(err.message || (isRegister ? "Registration failed. Please try again." : "Invalid email or password."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px 16px',
      background: 'var(--bg-app)'
    }}>
      <div
        className="wellness-card"
        style={{
          maxWidth: '460px',
          width: '100%',
          padding: '36px 32px',
          boxShadow: 'var(--shadow-lg)'
        }}
      >
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div style={{
            width: '52px',
            height: '52px',
            borderRadius: '16px',
            background: 'var(--primary-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 12px auto',
            boxShadow: '0 8px 20px rgba(31, 122, 90, 0.25)'
          }}>
            <Flame size={28} color="#FFFFFF" />
          </div>
          <h2 style={{ fontSize: '1.65rem', fontWeight: '800', margin: '0 0 4px 0', color: 'var(--text-primary)' }}>
            {isRegister ? 'Create your NutriQ Account' : 'Welcome back to NutriQ'}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', margin: 0 }}>
            {isRegister
              ? 'Personalized nutrition intelligence tailored to your goals.'
              : 'Sign in to access your nutrition journal and insights.'}
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div style={{
            padding: '12px 14px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--error-bg)',
            border: '1px solid rgba(217, 93, 93, 0.3)',
            color: 'var(--error-rose)',
            fontSize: '0.84rem',
            marginBottom: '18px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '8px'
          }}>
            <AlertCircle size={16} style={{ marginTop: '2px', flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Google Sign-In Button */}
        <button
          type="button"
          onClick={handleGoogleSignIn}
          disabled={googleLoading || loading}
          style={{
            width: '100%',
            height: '48px',
            borderRadius: '8px',
            background: '#FFFFFF',
            border: '1px solid #CBD5E1',
            color: '#111827',
            fontSize: '15px',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
            marginBottom: '20px',
            transition: 'all 0.16s ease',
            outline: 'none'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = '#F8FAFC';
            e.currentTarget.style.borderColor = '#94A3B8';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = '#FFFFFF';
            e.currentTarget.style.borderColor = '#CBD5E1';
          }}
          onMouseDown={(e) => {
            e.currentTarget.style.background = '#F1F5F9';
          }}
          onMouseUp={(e) => {
            e.currentTarget.style.background = '#F8FAFC';
          }}
        >
          <svg width="20" height="20" viewBox="0 0 48 48" style={{ flexShrink: 0 }}>
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            <path fill="none" d="M0 0h48v48H0z"/>
          </svg>
          <span style={{ color: '#111827', WebkitTextFillColor: '#111827', fontSize: '15px', fontWeight: '600' }}>
            {googleLoading ? 'Connecting with Google...' : 'Continue with Google'}
          </span>
        </button>

        {/* Separator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '20px' }}>
          <div style={{ flex: 1, height: '1px', background: 'var(--border-glass)' }} />
          <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            or continue with email
          </span>
          <div style={{ flex: 1, height: '1px', background: 'var(--border-glass)' }} />
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {isRegister && (
            <div>
              <label htmlFor="auth-name" style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Full Name *
              </label>
              <input
                id="auth-name"
                name="name"
                type="text"
                autoComplete="name"
                required
                className="input-field"
                placeholder="e.g. Harshath"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>
          )}

          <div>
            <label htmlFor="auth-email" style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              Email Address *
            </label>
            <input
              id="auth-email"
              name="email"
              type="email"
              autoComplete="email"
              required
              className="input-field"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus={!isRegister}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label htmlFor="auth-password" style={{ fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)' }}>
                Password *
              </label>
              {!isRegister && (
                <span
                  type="button"
                  onClick={() => navigate('/forgot-password')}
                  style={{
                    fontSize: '0.78rem',
                    fontWeight: '700',
                    color: 'var(--primary)',
                    cursor: 'pointer'
                  }}
                >
                  Forgot Password?
                </span>
              )}
            </div>
            <div style={{ position: 'relative' }}>
              <input
                id="auth-password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete={isRegister ? "new-password" : "current-password"}
                required
                minLength={6}
                className="input-field"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingRight: '40px' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '2px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                {showPassword ? <EyeOff size={16} color="var(--primary)" /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {isRegister && (
            <div>
              <label htmlFor="auth-confirm-password" style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Confirm Password *
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="auth-confirm-password"
                  name="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  minLength={6}
                  className="input-field"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  style={{ paddingRight: '40px' }}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: '2px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  {showConfirmPassword ? <EyeOff size={16} color="var(--primary)" /> : <Eye size={16} />}
                </button>
              </div>
            </div>
          )}

          {isRegister && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
              <label htmlFor="auth-terms" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <input
                  id="auth-terms"
                  name="terms"
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                  required
                  style={{ accentColor: 'var(--primary)', width: '16px', height: '16px' }}
                />
                <span>I agree to NutriQ Terms of Service and Privacy Policy</span>
              </label>
              <label htmlFor="auth-ai-consent" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                <input
                  id="auth-ai-consent"
                  name="ai_consent"
                  type="checkbox"
                  checked={aiConsentAccepted}
                  onChange={(e) => setAiConsentAccepted(e.target.checked)}
                  required
                  style={{ accentColor: 'var(--primary)', width: '16px', height: '16px' }}
                />
                <span>Enable AI-powered nutrition insights & companion</span>
              </label>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || googleLoading}
            className="btn-primary"
            style={{ width: '100%', padding: '12px', fontSize: '0.94rem', marginTop: '8px' }}
          >
            {loading ? 'Processing...' : (isRegister ? 'Create NutriQ Account' : 'Sign In')}
          </button>
        </form>

        {/* Footer Toggle */}
        <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          {isRegister ? (
            <>
              Already have an account?{' '}
              <span
                type="button"
                onClick={() => navigate('/login')}
                style={{ color: 'var(--primary)', fontWeight: '800', cursor: 'pointer' }}
              >
                Sign In
              </span>
            </>
          ) : (
            <>
              Don't have an account?{' '}
              <span
                type="button"
                onClick={() => navigate('/register')}
                style={{ color: 'var(--primary)', fontWeight: '800', cursor: 'pointer' }}
              >
                Sign Up
              </span>
            </>
          )}
        </div>

      </div>
    </div>
  );
};
