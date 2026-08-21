import React, { useState } from 'react';
import { api } from '../services/api';
import { useStore } from '../store/useStore';
import { Droplets, X, Plus, AlertCircle, CheckCircle } from 'lucide-react';

export const WaterModal = ({ isOpen, onClose, onWaterLogged, defaultDate = null }) => {
  const { targets, dailyAnalytics, refreshAllData } = useStore();
  const [selectedQuickAmount, setSelectedQuickAmount] = useState(250);
  const [customAmount, setCustomAmount] = useState('');
  const [isCustom, setIsCustom] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  if (!isOpen) return null;

  const targetDateStr = defaultDate || new Date().toISOString().split('T')[0];
  const waterConsumed = dailyAnalytics?.consumed?.water_ml || 0;
  const waterTarget = targets?.water_ml || 2500;
  const progressPct = waterTarget > 0 ? Math.min(100, Math.round((waterConsumed / waterTarget) * 100)) : 0;

  const quickAmounts = [250, 500, 750, 1000];

  const handleQuickSelect = (amt) => {
    setSelectedQuickAmount(amt);
    setIsCustom(false);
    setCustomAmount('');
    setErrorMessage('');
  };

  const handleCustomChange = (e) => {
    const val = e.target.value;
    setCustomAmount(val);
    setIsCustom(true);
    setErrorMessage('');
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    let amount = 0;
    if (isCustom) {
      if (!customAmount || customAmount.trim() === '') {
        setErrorMessage("Please enter a valid water amount.");
        return;
      }
      amount = parseFloat(customAmount);
      if (isNaN(amount) || amount <= 0) {
        setErrorMessage("Please enter a valid water amount greater than 0 ml.");
        return;
      }
      if (amount > 5000) {
        setErrorMessage("Water amount cannot exceed 5,000 ml per log entry.");
        return;
      }
    } else {
      amount = selectedQuickAmount;
    }

    if (!amount || amount <= 0) {
      setErrorMessage("Please enter a valid water amount.");
      return;
    }

    setLoading(true);
    try {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
      await api.logWater({
        amount_ml: amount,
        date: targetDateStr,
        time: timeStr
      });
      await refreshAllData();

      setSuccessMessage(`+${Math.round(amount)} ml added successfully!`);
      setTimeout(() => {
        if (onWaterLogged) onWaterLogged();
        onClose();
        setSuccessMessage('');
        setIsCustom(false);
        setCustomAmount('');
        setSelectedQuickAmount(250);
      }, 500);
    } catch (err) {
      console.error("Failed to log water:", err);
      setErrorMessage(err.message || "Failed to save water intake. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(23, 34, 29, 0.45)',
        backdropFilter: 'blur(6px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="wellness-card"
        style={{
          width: '100%',
          maxWidth: '440px',
          padding: '24px 28px',
          borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--border-glass)',
          background: 'var(--bg-card)',
          boxShadow: 'var(--shadow-lg)',
          animation: 'fadeIn 0.2s ease-out'
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: 'var(--hydration-gradient)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 4px 12px rgba(21, 154, 156, 0.3)'
              }}
            >
              <Droplets size={20} color="#fff" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>Water Intake</h3>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Track your hydration
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="btn-secondary"
            style={{
              border: 'none',
              borderRadius: '50%',
              width: '32px',
              height: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: 0
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Current Status Indicator */}
        <div
          style={{
            background: 'var(--hydration-cyan-light)',
            border: '1px solid rgba(21, 154, 156, 0.25)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 16px',
            marginBottom: '20px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: '600' }}>
              Today's intake:
            </span>
            <span style={{ fontSize: '0.92rem', fontWeight: '800', color: 'var(--hydration-cyan)' }}>
              {Math.round(waterConsumed).toLocaleString()} / {Math.round(waterTarget).toLocaleString()} ml ({progressPct}%)
            </span>
          </div>
          <div style={{ height: '6px', background: 'var(--bg-elevated, #FFFFFF)', borderRadius: '3px', overflow: 'hidden' }}>
            <div
              style={{
                height: '100%',
                width: `${progressPct}%`,
                background: 'var(--hydration-gradient)',
                borderRadius: '3px',
                transition: 'width 0.3s ease'
              }}
            />
          </div>
        </div>

        {/* Error / Success feedback */}
        {errorMessage && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--error-bg)',
              border: '1px solid rgba(220, 76, 76, 0.3)',
              color: 'var(--error-rose)',
              fontSize: '0.82rem',
              marginBottom: '16px'
            }}
          >
            <AlertCircle size={15} style={{ flexShrink: 0 }} />
            <span>{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 14px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--success-bg)',
              border: '1px solid var(--border-glass)',
              color: 'var(--success)',
              fontSize: '0.82rem',
              marginBottom: '16px'
            }}
          >
            <CheckCircle size={15} style={{ flexShrink: 0 }} />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Quick-Add Buttons */}
        <div style={{ marginBottom: '18px' }}>
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            Quick Select
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
            {quickAmounts.map((amt) => {
              const isSelected = !isCustom && selectedQuickAmount === amt;
              return (
                <button
                  key={amt}
                  type="button"
                  onClick={() => handleQuickSelect(amt)}
                  style={{
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-md)',
                    border: isSelected ? '2px solid var(--hydration-cyan)' : '1px solid var(--border-glass)',
                    background: isSelected ? 'var(--hydration-cyan-light)' : 'var(--bg-subtle)',
                    color: isSelected ? 'var(--hydration-cyan)' : 'var(--text-primary)',
                    fontWeight: isSelected ? '800' : '600',
                    fontSize: '0.92rem',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  +{amt} ml
                </button>
              );
            })}
          </div>
        </div>

        {/* Custom Amount */}
        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            Custom Amount
          </label>
          <div style={{ position: 'relative' }}>
            <input
              type="number"
              placeholder="e.g. 350"
              value={customAmount}
              onChange={handleCustomChange}
              onFocus={() => setIsCustom(true)}
              min="1"
              max="5000"
              className="input-field"
              style={{
                width: '100%',
                padding: '12px 42px 12px 14px',
                borderRadius: 'var(--radius-md)',
                borderColor: isCustom ? 'var(--hydration-cyan)' : 'var(--border-glass)',
                fontSize: '0.95rem'
              }}
            />
            <span
              style={{
                position: 'absolute',
                right: '14px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
                fontSize: '0.85rem',
                fontWeight: '600'
              }}
            >
              ml
            </span>
          </div>
        </div>

        {/* Buttons: Cancel & Add Water */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="btn-secondary"
            style={{ padding: '12px', fontSize: '0.9rem', justifyContent: 'center' }}
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="btn-primary"
            style={{
              padding: '12px',
              fontSize: '0.9rem',
              justifyContent: 'center',
              background: 'var(--hydration-gradient)',
              borderColor: 'transparent'
            }}
          >
            {loading ? 'Adding...' : 'Add Water'}
          </button>
        </div>
      </div>
    </div>
  );
};
