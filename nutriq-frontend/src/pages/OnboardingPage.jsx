import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import {
  User, Activity, Target, Utensils, CheckCircle2,
  ArrowRight, ArrowLeft, Sparkles, Flame, AlertCircle
} from 'lucide-react';

export const OnboardingPage = ({ onComplete }) => {
  const { profile, refreshAllData, navigate } = useStore();

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const [formData, setFormData] = useState({
    name: profile?.name || '',
    age: profile?.age ? String(profile.age) : '',
    gender: profile?.gender || '',
    height_cm: profile?.height_cm ? String(profile.height_cm) : '',
    weight_kg: profile?.weight_kg ? String(profile.weight_kg) : '',
    activity_level: profile?.activity_level || '',
    fitness_goal: profile?.fitness_goal || '',
    desired_rate: 0.5,
    dietary_preference: profile?.dietary_preference || 'standard',
    food_preferences: profile?.food_preferences || ''
  });

  useEffect(() => {
    if (profile) {
      setFormData(prev => ({
        ...prev,
        name: prev.name || profile.name || '',
        age: prev.age || (profile.age ? String(profile.age) : ''),
        gender: prev.gender || profile.gender || '',
        height_cm: prev.height_cm || (profile.height_cm ? String(profile.height_cm) : ''),
        weight_kg: prev.weight_kg || (profile.weight_kg ? String(profile.weight_kg) : ''),
        activity_level: prev.activity_level || profile.activity_level || '',
        fitness_goal: prev.fitness_goal || profile.fitness_goal || '',
        dietary_preference: prev.dietary_preference || profile.dietary_preference || 'standard'
      }));
    }
  }, [profile]);

  const validateStep = (currentStep) => {
    if (currentStep === 1) {
      if (!formData.name.trim()) return "Please enter your full name.";
      const ageNum = parseInt(formData.age, 10);
      if (!formData.age || isNaN(ageNum) || ageNum < 10 || ageNum > 120) return "Please enter a valid age between 10 and 120 years.";
      if (!formData.gender) return "Please select your biological sex.";
    }
    if (currentStep === 2) {
      const heightNum = parseFloat(formData.height_cm);
      const weightNum = parseFloat(formData.weight_kg);
      if (!formData.height_cm || isNaN(heightNum) || heightNum < 50 || heightNum > 280) return "Please enter a valid height in cm (50 - 280 cm).";
      if (!formData.weight_kg || isNaN(weightNum) || weightNum < 20 || weightNum > 400) return "Please enter a valid weight in kg (20 - 400 kg).";
    }
    if (currentStep === 3) {
      if (!formData.activity_level) return "Please select your daily activity level.";
      if (!formData.fitness_goal) return "Please select your primary fitness goal.";
    }
    return null;
  };

  const handleNext = () => {
    const err = validateStep(step);
    if (err) {
      setErrorMsg(err);
      return;
    }
    setErrorMsg(null);
    setStep(prev => prev + 1);
  };

  const handleBack = () => {
    setErrorMsg(null);
    setStep(prev => Math.max(1, prev - 1));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const err = validateStep(3);
    if (err) {
      setErrorMsg(err);
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    try {
      await api.createProfile({
        name: formData.name.trim(),
        age: parseInt(formData.age, 10),
        gender: formData.gender,
        height_cm: parseFloat(formData.height_cm),
        weight_kg: parseFloat(formData.weight_kg),
        activity_level: formData.activity_level,
        fitness_goal: formData.fitness_goal,
        dietary_preference: formData.dietary_preference
      });

      await refreshAllData();
      if (onComplete) onComplete();
      else navigate('/dashboard');
    } catch (err) {
      setErrorMsg(err.message || "Failed to initialize profile. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '600px', margin: '40px auto', width: '100%', padding: '0 16px' }}>
      <div className="wellness-card" style={{ padding: '36px 32px' }}>
        
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div style={{
            width: '52px', height: '52px', borderRadius: '16px',
            background: 'var(--primary-gradient)',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 8px 20px rgba(31, 122, 90, 0.25)', marginBottom: '12px'
          }}>
            <Flame size={28} color="#FFFFFF" />
          </div>
          <h2 style={{ fontSize: '1.6rem', fontWeight: '800', margin: '0 0 6px 0', color: 'var(--text-primary)' }}>
            Personalize Your Nutrition Profile
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', margin: 0 }}>
            Step {step} of 3 • Accurate scientific equations for your energy needs
          </p>
        </div>

        {/* Step Progress Bar */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '28px' }}>
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              style={{
                flex: 1,
                height: '6px',
                borderRadius: '9999px',
                background: s <= step ? 'var(--primary)' : 'var(--border-glass)',
                transition: 'all 0.3s ease'
              }}
            />
          ))}
        </div>

        {errorMsg && (
          <div style={{
            padding: '12px 14px', borderRadius: 'var(--radius-md)',
            background: 'var(--error-bg)', border: '1px solid rgba(217, 93, 93, 0.3)',
            color: 'var(--error-rose)', fontSize: '0.84rem', marginBottom: '20px',
            display: 'flex', alignItems: 'center', gap: '8px'
          }}>
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Step 1: Identity */}
        {step === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Your Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="input-field"
                placeholder="e.g. Alex Morgan"
                autoFocus
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Age (years) *
              </label>
              <input
                type="number"
                value={formData.age}
                onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                className="input-field"
                placeholder="e.g. 26"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Biological Sex *
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                {['male', 'female'].map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setFormData({ ...formData, gender: g })}
                    className={formData.gender === g ? "btn-primary" : "btn-secondary"}
                    style={{ padding: '12px', fontSize: '0.88rem', textTransform: 'capitalize' }}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Body Metrics */}
        {step === 2 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Height (cm) *
              </label>
              <input
                type="number"
                step="0.5"
                value={formData.height_cm}
                onChange={(e) => setFormData({ ...formData, height_cm: e.target.value })}
                className="input-field"
                placeholder="e.g. 175"
                autoFocus
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Weight (kg) *
              </label>
              <input
                type="number"
                step="0.1"
                value={formData.weight_kg}
                onChange={(e) => setFormData({ ...formData, weight_kg: e.target.value })}
                className="input-field"
                placeholder="e.g. 70"
              />
            </div>
          </div>
        )}

        {/* Step 3: Activity & Goals */}
        {step === 3 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Daily Activity Level *
              </label>
              <select
                value={formData.activity_level}
                onChange={(e) => setFormData({ ...formData, activity_level: e.target.value })}
                className="input-field"
              >
                <option value="">Select activity level</option>
                <option value="sedentary">Sedentary (mostly sitting)</option>
                <option value="lightly_active">Lightly Active (1-3 workouts/week)</option>
                <option value="moderately_active">Moderately Active (3-5 workouts/week)</option>
                <option value="very_active">Very Active (6-7 intense sessions/week)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Primary Fitness Goal *
              </label>
              <select
                value={formData.fitness_goal}
                onChange={(e) => setFormData({ ...formData, fitness_goal: e.target.value })}
                className="input-field"
              >
                <option value="">Select goal</option>
                <option value="weight_loss">Weight Loss</option>
                <option value="maintain">Maintain Weight</option>
                <option value="muscle_building">Muscle Building</option>
                <option value="weight_gain">Weight Gain</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Dietary Preference
              </label>
              <select
                value={formData.dietary_preference}
                onChange={(e) => setFormData({ ...formData, dietary_preference: e.target.value })}
                className="input-field"
              >
                <option value="standard">Standard / Non-Vegetarian</option>
                <option value="vegetarian">Vegetarian</option>
                <option value="vegan">Vegan</option>
                <option value="eggetarian">Eggetarian</option>
              </select>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '28px', paddingTop: '16px', borderTop: '1px solid var(--border-glass)' }}>
          {step > 1 ? (
            <button
              type="button"
              onClick={handleBack}
              className="btn-secondary"
              style={{ padding: '10px 18px' }}
            >
              <ArrowLeft size={16} /> Back
            </button>
          ) : <div />}

          {step < 3 ? (
            <button
              type="button"
              onClick={handleNext}
              className="btn-primary"
              style={{ padding: '10px 22px' }}
            >
              Next <ArrowRight size={16} />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading}
              className="btn-primary"
              style={{ padding: '10px 24px' }}
            >
              {loading ? 'Saving Setup...' : 'Complete Setup & Launch Dashboard'}
            </button>
          )}
        </div>

      </div>
    </div>
  );
};
