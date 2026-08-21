import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { KeyRound, ArrowRight, ArrowLeft, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

export const ForgotPasswordPage = () => {
  const { navigate } = useStore();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim() || !emailRegex.test(email.trim())) {
      setError("Please enter a valid email address.");
      return;
    }

    setLoading(true);

    try {
      await api.forgotPassword(email);
      setSubmitted(true);
    } catch (err) {
      setError(err.message || "Failed to send reset link. Please try again.");
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
            <KeyRound size={26} color="#FFFFFF" />
          </div>
          <h2 style={{ fontSize: '1.6rem', fontWeight: '800', margin: '0 0 8px 0', color: 'var(--text-primary)' }}>
            Forgot Password
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', lineHeight: '1.5', margin: 0 }}>
            Enter the email address associated with your NutriQ account to receive a secure reset link.
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div style={{
            padding: '12px 14px', borderRadius: 'var(--radius-md)',
            background: 'var(--error-bg)', border: '1px solid rgba(217, 93, 93, 0.3)',
            color: 'var(--error-rose)', fontSize: '0.84rem', marginBottom: '20px',
            display: 'flex', alignItems: 'flex-start', gap: '8px'
          }}>
            <AlertCircle size={16} style={{ marginTop: '2px', flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Success State */}
        {submitted ? (
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
              Check your inbox
            </h3>

            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: '1.5', marginBottom: '24px' }}>
              If an account exists for <strong>{email}</strong>, we've sent a password reset link.
            </p>

            <button
              type="button"
              onClick={() => navigate('/login')}
              className="btn-primary"
              style={{ width: '100%', padding: '12px', fontSize: '0.92rem' }}
            >
              <ArrowLeft size={16} style={{ marginRight: '6px' }} />
              Back to Login
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label htmlFor="forgot-email" style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Email Address *
              </label>
              <input
                id="forgot-email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="input-field"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
              style={{ width: '100%', padding: '12px', marginTop: '6px', fontSize: '0.94rem' }}
            >
              {loading ? 'Sending link...' : 'Send Reset Link'}
            </button>

            <div style={{ textAlign: 'center', marginTop: '10px' }}>
              <span
                onClick={() => navigate('/login')}
                style={{
                  color: 'var(--primary)',
                  fontSize: '0.86rem',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <ArrowLeft size={14} /> Back to Login
              </span>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
