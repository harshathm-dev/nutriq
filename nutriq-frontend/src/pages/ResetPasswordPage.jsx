import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { Lock, ArrowRight, ArrowLeft, CheckCircle2, AlertCircle, Loader2, ShieldCheck, Eye, EyeOff } from 'lucide-react';

export const ResetPasswordPage = () => {
  const { navigate } = useStore();
  
  const [token, setToken] = useState('');
  const [validating, setValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [tokenError, setTokenError] = useState(null);
  const [userEmail, setUserEmail] = useState(null);

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get('token');

    if (!urlToken || !urlToken.trim()) {
      setValidating(false);
      setTokenValid(false);
      setTokenError("Missing password reset token. Please request a new password reset link.");
      return;
    }

    setToken(urlToken.trim());

    const checkToken = async () => {
      try {
        const res = await api.validateResetToken(urlToken.trim());
        if (res.valid) {
          setTokenValid(true);
          setUserEmail(res.email);
        } else {
          setTokenValid(false);
          if (res.reason === 'expired') {
            setTokenError("Your password reset link has expired. Please request a new one.");
          } else if (res.reason === 'used') {
            setTokenError("Your password reset link is no longer valid because it has already been used. Please request a new one.");
          } else {
            setTokenError("Your password reset link is invalid. Please request a new one.");
          }
        }
      } catch (e) {
        setTokenValid(false);
        setTokenError("Unable to verify reset link. Please check your connection.");
      } finally {
        setValidating(false);
      }
    };

    checkToken();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);

    if (!password || password.length < 6) {
      setFormError("Password must be at least 6 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setFormError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await api.resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      setFormError(err.message || "Failed to reset password. The link may have expired.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '85vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px 16px', background: 'var(--bg-app)' }}>
      <div className="wellness-card" style={{ width: '100%', maxWidth: '460px', padding: '36px 32px' }}>
        
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div
            onClick={() => navigate('/welcome')}
            style={{
              width: '52px', height: '52px', borderRadius: '16px',
              background: 'var(--primary-gradient)',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 8px 20px rgba(31, 122, 90, 0.25)', marginBottom: '14px',
              cursor: 'pointer'
            }}
          >
            <ShieldCheck size={26} color="#FFFFFF" />
          </div>
          <h2 style={{ fontSize: '1.6rem', fontWeight: '800', margin: '0 0 8px 0', color: 'var(--text-primary)' }}>
            Reset Password
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', lineHeight: '1.5', margin: 0 }}>
            {userEmail ? `Enter a new password for ${userEmail}` : 'Create a new secure password for your NutriQ account.'}
          </p>
        </div>

        {validating ? (
          <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text-secondary)' }}>
            Verifying security token...
          </div>
        ) : !tokenValid ? (
          <div style={{ textAlign: 'center', padding: '10px 0' }}>
            <div style={{
              padding: '12px 14px', borderRadius: 'var(--radius-md)',
              background: 'var(--error-bg)', border: '1px solid rgba(217, 93, 93, 0.3)',
              color: 'var(--error-rose)', fontSize: '0.86rem', marginBottom: '20px'
            }}>
              {tokenError}
            </div>

            <button
              type="button"
              onClick={() => navigate('/forgot-password')}
              className="btn-primary"
              style={{ width: '100%', padding: '12px', fontSize: '0.92rem' }}
            >
              Request New Reset Link
            </button>
          </div>
        ) : success ? (
          <div style={{ textAlign: 'center', padding: '10px 0' }}>
            <div style={{
              width: '52px', height: '52px', borderRadius: '50%',
              background: 'var(--primary-light)',
              color: 'var(--primary)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: '16px'
            }}>
              <CheckCircle2 size={30} />
            </div>

            <h3 style={{ fontSize: '1.15rem', fontWeight: '800', marginBottom: '8px', color: 'var(--text-primary)' }}>
              Password Reset Successfully
            </h3>

            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: '1.5', marginBottom: '24px' }}>
              Your password has been updated. You can now log in with your new credentials.
            </p>

            <button
              type="button"
              onClick={() => navigate('/login')}
              className="btn-primary"
              style={{ width: '100%', padding: '12px', fontSize: '0.92rem' }}
            >
              Sign In to NutriQ
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {formError && (
              <div style={{
                padding: '12px 14px', borderRadius: 'var(--radius-md)',
                background: 'var(--error-bg)', border: '1px solid rgba(217, 93, 93, 0.3)',
                color: 'var(--error-rose)', fontSize: '0.84rem'
              }}>
                {formError}
              </div>
            )}

            <div>
              <label htmlFor="reset-new-password" style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                New Password *
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="reset-new-password"
                  name="new_password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  minLength={6}
                  className="input-field"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{ paddingRight: '40px' }}
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  style={{
                    position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                    background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px'
                  }}
                >
                  {showPassword ? <EyeOff size={16} color="var(--primary)" /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div>
              <label htmlFor="reset-confirm-password" style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Confirm New Password *
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="reset-confirm-password"
                  name="confirm_password"
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
                    position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                    background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px'
                  }}
                >
                  {showConfirmPassword ? <EyeOff size={16} color="var(--primary)" /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
              style={{ width: '100%', padding: '12px', marginTop: '6px', fontSize: '0.94rem' }}
            >
              {loading ? 'Saving new password...' : 'Update Password'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default ResetPasswordPage;
