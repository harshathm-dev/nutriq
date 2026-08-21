import React from 'react';
import { useStore } from '../store/useStore';
import {
  Flame, ArrowRight, LogIn, Sparkles, UtensilsCrossed,
  BrainCircuit, CalendarDays, LineChart, ShieldCheck, CheckCircle2,
  ChevronRight, HeartPulse
} from 'lucide-react';

export const WelcomePage = () => {
  const { navigate } = useStore();

  const capabilities = [
    {
      icon: HeartPulse,
      title: 'Personalized Targets',
      description: 'Deterministic metabolic equations (BMR, TDEE) customized specifically for your physical profile and goal pace.',
      color: '#167C5A',
      bg: 'var(--primary-light)'
    },
    {
      icon: BrainCircuit,
      title: 'NutriQ AI Companion',
      description: 'Conversational nutrition coach powered by Gemini with deep grounding in your calorie budget and meal logs.',
      color: '#7357D9',
      bg: 'var(--ai-violet-light)'
    },
    {
      icon: UtensilsCrossed,
      title: 'Multi-Channel Food Logging',
      description: 'Verified Indian food database with complete macronutrient profiles and local offline synchronization.',
      color: '#159A9C',
      bg: 'var(--hydration-cyan-light)'
    },
    {
      icon: CalendarDays,
      title: 'Weekly Meal Planning',
      description: 'Automated 7-day meal schedules designed around regional dietary preferences and allergy constraints.',
      color: '#D97706',
      bg: 'var(--warning-amber-light)'
    },
    {
      icon: LineChart,
      title: 'Progress Analytics',
      description: 'Grounded macronutrient balance curves, hydration trackers, safe weight projections, and habit streaks.',
      color: '#3B73E8',
      bg: 'var(--macro-protein-light)'
    }
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-app)' }}>
      
      {/* Top Welcome Header */}
      <header
        className="wellness-card"
        style={{
          margin: '16px 24px 0 24px',
          padding: '14px 28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          zIndex: 50
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'var(--primary-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(31, 122, 90, 0.25)'
          }}>
            <Flame size={24} color="#FFFFFF" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.3rem', fontWeight: '800', color: 'var(--primary)', margin: 0 }}>
              NutriQ
            </h1>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: '600' }}>
              Personal Nutrition Intelligence
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="btn-secondary"
            style={{ padding: '8px 18px', fontSize: '0.86rem' }}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => navigate('/register')}
            className="btn-primary"
            style={{ padding: '8px 20px', fontSize: '0.86rem', gap: '6px' }}
          >
            Get Started <ArrowRight size={15} />
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 24px 60px 24px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
        <div style={{ textAlign: 'center', maxWidth: '820px', marginTop: '20px', marginBottom: '48px' }}>
          
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '6px 14px', borderRadius: 'var(--radius-full)', background: 'var(--primary-light)', color: 'var(--primary-dark)', fontSize: '0.8rem', fontWeight: '800', marginBottom: '20px' }}>
            <Sparkles size={15} />
            Modern Natural Wellness Platform
          </div>

          <h2 style={{
            fontSize: 'clamp(2.2rem, 5vw, 3.4rem)',
            fontWeight: '800',
            lineHeight: 1.15,
            letterSpacing: '-0.03em',
            marginBottom: '20px',
            color: 'var(--text-primary)'
          }}>
            Mindful Nutrition Guided by <span style={{ color: 'var(--primary)' }}>Personal Intelligence</span>
          </h2>

          <p style={{
            fontSize: 'clamp(1rem, 2vw, 1.15rem)',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
            marginBottom: '32px',
            maxWidth: '680px',
            marginInline: 'auto'
          }}>
            Track your meals, understand your macronutrients, design personalized meal plans, and build lasting healthy habits with verifiable scientific guidance.
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', justifyContent: 'center', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => navigate('/register')}
              className="btn-primary"
              style={{
                padding: '12px 30px',
                fontSize: '1.02rem',
                gap: '8px'
              }}
            >
              Start Free Today <ArrowRight size={18} />
            </button>

            <button
              type="button"
              onClick={() => navigate('/login')}
              className="btn-secondary"
              style={{
                padding: '12px 26px',
                fontSize: '1.02rem'
              }}
            >
              Sign In
            </button>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '20px', marginTop: '24px', color: 'var(--text-muted)', fontSize: '0.82rem', flexWrap: 'wrap' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={14} color="var(--primary)" /> 100% Grounded Calculations
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={14} color="var(--primary)" /> Verified Indian Foods
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={14} color="var(--primary)" /> Offline-First Sync
            </span>
          </div>
        </div>

        {/* Capabilities Grid */}
        <section style={{ width: '100%', marginTop: '10px' }}>
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <h3 style={{ fontSize: '1.5rem', fontWeight: '800', marginBottom: '8px', color: 'var(--text-primary)' }}>
              Core Intelligence Modules
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem' }}>
              Engineered for health precision, deterministic science, and daily habit consistency.
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '20px',
            width: '100%'
          }}>
            {capabilities.map((cap, index) => {
              const Icon = cap.icon;
              return (
                <div
                  key={index}
                  className="wellness-card"
                  style={{
                    padding: '24px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '16px'
                  }}
                >
                  <div>
                    <div style={{
                      width: '46px',
                      height: '46px',
                      borderRadius: '12px',
                      background: cap.bg,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginBottom: '16px',
                      color: cap.color
                    }}>
                      <Icon size={24} />
                    </div>

                    <h4 style={{ fontSize: '1.12rem', fontWeight: '800', marginBottom: '8px', color: 'var(--text-primary)' }}>
                      {cap.title}
                    </h4>

                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', lineHeight: 1.55 }}>
                      {cap.description}
                    </p>
                  </div>

                  <div style={{ paddingTop: '12px', borderTop: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: cap.color, fontSize: '0.8rem', fontWeight: '700' }}>
                    <span>Included in NutriQ</span>
                    <ChevronRight size={15} />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', borderTop: '1px solid var(--border-glass)' }}>
        © {new Date().getFullYear()} NutriQ — AI Nutrition Intelligence Platform. All rights reserved.
      </footer>
    </div>
  );
};
