import React, { useState } from 'react';
import { CreditCard, Check, Sparkles, Shield, Zap } from 'lucide-react';

export const BillingPage = () => {
  const [currentPlan, setCurrentPlan] = useState('free');
  const [usedToday, setUsedToday] = useState(3);
  const dailyQuota = currentPlan === 'premium' ? 200 : 15;

  const handleUpgrade = (tier) => {
    setCurrentPlan(tier);
    alert(`Successfully activated ${tier.toUpperCase()} Plan!`);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
          <CreditCard size={24} color="#f59e0b" />
          <h2 style={{ fontSize: '1.4rem' }}>Subscription & AI Usage Controls</h2>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Transparent AI usage metering, quota limits, and plan tier management.
        </p>
      </div>

      {/* AI Usage Meter */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div>
            <div style={{ fontSize: '1rem', fontWeight: '700' }}>Today's AI Intelligence Usage</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Natural language extraction, meal planning, and chat tokens
            </div>
          </div>
          <div style={{ fontSize: '1.2rem', fontWeight: '800', color: '#60a5fa' }}>
            {usedToday} / {dailyQuota} requests
          </div>
        </div>

        <div style={{ width: '100%', height: '10px', background: 'rgba(255,255,255,0.08)', borderRadius: '6px', overflow: 'hidden' }}>
          <div
            style={{
              width: `${(usedToday / dailyQuota) * 100}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
              borderRadius: '6px'
            }}
          />
        </div>
      </div>

      {/* Plan Tiers Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        
        {/* Free Plan */}
        <div
          className="glass-panel"
          style={{
            padding: '28px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
            borderColor: currentPlan === 'free' ? '#10b981' : 'var(--border-glass)'
          }}
        >
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h3 style={{ fontSize: '1.25rem' }}>Starter (Free)</h3>
              {currentPlan === 'free' && <span className="badge badge-emerald">Current Plan</span>}
            </div>
            <div style={{ fontSize: '1.8rem', fontWeight: '800', marginBottom: '16px' }}>
              $0 <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: '400' }}>/ forever</span>
            </div>

            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Check size={16} color="#10b981" /> Full deterministic Mifflin-St Jeor calculations
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Check size={16} color="#10b981" /> Complete IFCT & Barcode Food Logging
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Check size={16} color="#10b981" /> Offline IndexedDB PWA tracking & sync
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Check size={16} color="#10b981" /> 15 AI extraction & chat requests / day
              </li>
            </ul>
          </div>

          <button
            disabled={currentPlan === 'free'}
            onClick={() => handleUpgrade('free')}
            className="btn-secondary"
            style={{ width: '100%', marginTop: '24px' }}
          >
            {currentPlan === 'free' ? 'Active Plan' : 'Downgrade to Free'}
          </button>
        </div>

        {/* Premium Plan */}
        <div
          className="glass-panel"
          style={{
            padding: '28px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.12), rgba(59, 130, 246, 0.08))',
            borderColor: currentPlan === 'premium' ? '#8b5cf6' : 'rgba(139, 92, 246, 0.4)'
          }}
        >
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <h3 style={{ fontSize: '1.25rem', color: '#c084fc' }}>NutriQ Pro Intelligence</h3>
              {currentPlan === 'premium' ? (
                <span className="badge badge-blue">Active</span>
              ) : (
                <span className="badge badge-amber">Recommended</span>
              )}
            </div>
            <div style={{ fontSize: '1.8rem', fontWeight: '800', marginBottom: '16px' }}>
              $9.99 <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: '400' }}>/ month</span>
            </div>

            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Check size={16} color="#8b5cf6" /> <strong>200 AI Claude 3.7 Requests</strong> daily
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Check size={16} color="#8b5cf6" /> Unlimited 7-Day Personalized Meal Plans
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Check size={16} color="#8b5cf6" /> Priority Cloud & Offline Bi-Directional Sync
              </li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Check size={16} color="#8b5cf6" /> Advanced weekly habit & pattern reports
              </li>
            </ul>
          </div>

          <button
            onClick={() => handleUpgrade(currentPlan === 'premium' ? 'free' : 'premium')}
            className="btn-primary"
            style={{ width: '100%', marginTop: '24px', background: 'linear-gradient(135deg, #8b5cf6, #6366f1)' }}
          >
            <Sparkles size={16} />
            {currentPlan === 'premium' ? 'Cancel Subscription' : 'Upgrade to Pro'}
          </button>
        </div>

      </div>
    </div>
  );
};
