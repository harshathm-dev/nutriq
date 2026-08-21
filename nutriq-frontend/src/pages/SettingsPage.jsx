import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import {
  Settings, User, Sliders, CheckCircle2, Shield, RefreshCw,
  Bell, Clock, Moon, Sun, AlertCircle, Sparkles, Check
} from 'lucide-react';

export const SettingsPage = () => {
  const {
    profile, targets, reminderSettings, setProfile,
    updateReminderSettings, refreshAllData, theme, setTheme,
    isOnline, syncPendingCount, triggerSync
  } = useStore();

  // Profile State
  const [name, setName] = useState(profile?.name || '');
  const [age, setAge] = useState(profile?.age || 25);
  const [gender, setGender] = useState(profile?.gender || 'male');
  const [heightCm, setHeightCm] = useState(profile?.height_cm || 175.0);
  const [weightKg, setWeightKg] = useState(profile?.weight_kg || 70.0);
  const [activityLevel, setActivityLevel] = useState(profile?.activity_level || 'moderately_active');
  const [fitnessGoal, setFitnessGoal] = useState(profile?.fitness_goal || 'maintain');
  const [dietaryPref, setDietaryPref] = useState(profile?.dietary_preference || 'standard');
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);

  // Reminder Settings State
  const [remindersEnabled, setRemindersEnabled] = useState(reminderSettings?.reminders_enabled ?? true);
  const [breakfastEnabled, setBreakfastEnabled] = useState(reminderSettings?.breakfast_enabled ?? true);
  const [breakfastTime, setBreakfastTime] = useState(reminderSettings?.breakfast_time || '08:00');
  const [lunchEnabled, setLunchEnabled] = useState(reminderSettings?.lunch_enabled ?? true);
  const [lunchTime, setLunchTime] = useState(reminderSettings?.lunch_time || '13:00');
  const [snackEnabled, setSnackEnabled] = useState(reminderSettings?.snack_enabled ?? true);
  const [snackTime, setSnackTime] = useState(reminderSettings?.snack_time || '17:00');
  const [dinnerEnabled, setDinnerEnabled] = useState(reminderSettings?.dinner_enabled ?? true);
  const [dinnerTime, setDinnerTime] = useState(reminderSettings?.dinner_time || '20:00');
  const [savingReminders, setSavingReminders] = useState(false);
  const [savedReminders, setSavedReminders] = useState(false);

  useEffect(() => {
    const loadReminders = async () => {
      try {
        const settings = await api.getReminderSettings();
        if (settings) {
          setRemindersEnabled(settings.reminders_enabled ?? true);
          setBreakfastEnabled(settings.breakfast_enabled ?? true);
          setBreakfastTime(settings.breakfast_time || '08:00');
          setLunchEnabled(settings.lunch_enabled ?? true);
          setLunchTime(settings.lunch_time || '13:00');
          setSnackEnabled(settings.snack_enabled ?? true);
          setSnackTime(settings.snack_time || '17:00');
          setDinnerEnabled(settings.dinner_enabled ?? true);
          setDinnerTime(settings.dinner_time || '20:00');
        }
      } catch (err) {
        console.warn("Could not fetch reminders:", err);
      }
    };
    if (reminderSettings) {
      setRemindersEnabled(reminderSettings.reminders_enabled ?? true);
      setBreakfastEnabled(reminderSettings.breakfast_enabled ?? true);
      setBreakfastTime(reminderSettings.breakfast_time || '08:00');
      setLunchEnabled(reminderSettings.lunch_enabled ?? true);
      setLunchTime(reminderSettings.lunch_time || '13:00');
      setSnackEnabled(reminderSettings.snack_enabled ?? true);
      setSnackTime(reminderSettings.snack_time || '17:00');
      setDinnerEnabled(reminderSettings.dinner_enabled ?? true);
      setDinnerTime(reminderSettings.dinner_time || '20:00');
    } else {
      loadReminders();
    }
  }, [reminderSettings]);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSaved(false);
    try {
      const updated = await api.updateProfile({
        name,
        age: parseInt(age),
        gender,
        height_cm: parseFloat(heightCm),
        weight_kg: parseFloat(weightKg),
        activity_level: activityLevel,
        fitness_goal: fitnessGoal,
        dietary_preference: dietaryPref
      });
      setProfile(updated);
      await refreshAllData();
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      alert("Failed to update profile.");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveReminders = async (e) => {
    e.preventDefault();
    setSavingReminders(true);
    setSavedReminders(false);
    try {
      await updateReminderSettings({
        reminders_enabled: remindersEnabled,
        breakfast_enabled: breakfastEnabled,
        breakfast_time: breakfastTime,
        lunch_enabled: lunchEnabled,
        lunch_time: lunchTime,
        snack_enabled: snackEnabled,
        snack_time: snackTime,
        dinner_enabled: dinnerEnabled,
        dinner_time: dinnerTime
      });
      setSavedReminders(true);
      setTimeout(() => setSavedReminders(false), 3000);
    } catch (err) {
      alert("Failed to update reminder settings.");
    } finally {
      setSavingReminders(false);
    }
  };

  return (
    <div className="page-container" style={{ maxWidth: '1200px' }}>
      
      {/* 1. Header Banner */}
      <div className="wellness-card" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '42px', height: '42px', borderRadius: '12px',
            background: 'var(--primary-gradient)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(31, 122, 90, 0.25)'
          }}>
            <Settings size={22} color="#FFFFFF" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
              Settings & Preferences
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', margin: 0 }}>
              Manage your biometric parameters, nutrition goals, reminder schedules, and theme preferences.
            </p>
          </div>
        </div>
      </div>

      {/* 2. Biometric Profile Settings */}
      <div className="wellness-card" style={{ padding: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
              Biometric Profile & Nutrition Goals
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Mifflin-St Jeor metabolic target recalculated automatically on save
            </span>
          </div>
          {saved && (
            <span className="badge badge-emerald">
              <Check size={14} /> Profile Saved
            </span>
          )}
        </div>

        <form onSubmit={handleSaveProfile} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Full Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-field"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Age
              </label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                className="input-field"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Biological Sex
              </label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="input-field"
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Height (cm)
              </label>
              <input
                type="number"
                step="0.5"
                value={heightCm}
                onChange={(e) => setHeightCm(e.target.value)}
                className="input-field"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Weight (kg)
              </label>
              <input
                type="number"
                step="0.1"
                value={weightKg}
                onChange={(e) => setWeightKg(e.target.value)}
                className="input-field"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Activity Level
              </label>
              <select
                value={activityLevel}
                onChange={(e) => setActivityLevel(e.target.value)}
                className="input-field"
              >
                <option value="sedentary">Sedentary (desk job)</option>
                <option value="lightly_active">Lightly Active (1-3 days/wk)</option>
                <option value="moderately_active">Moderately Active (3-5 days/wk)</option>
                <option value="very_active">Very Active (6-7 days/wk)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Primary Goal
              </label>
              <select
                value={fitnessGoal}
                onChange={(e) => setFitnessGoal(e.target.value)}
                className="input-field"
              >
                <option value="weight_loss">Weight Loss</option>
                <option value="maintain">Maintenance</option>
                <option value="muscle_building">Muscle Building</option>
                <option value="weight_gain">Weight Gain</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Dietary Preference
              </label>
              <select
                value={dietaryPref}
                onChange={(e) => setDietaryPref(e.target.value)}
                className="input-field"
              >
                <option value="standard">Standard / Non-Vegetarian</option>
                <option value="vegetarian">Vegetarian</option>
                <option value="vegan">Vegan</option>
                <option value="eggetarian">Eggetarian</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
            <button type="submit" disabled={loading} className="btn-primary" style={{ padding: '10px 22px' }}>
              {loading ? 'Saving Profile...' : 'Save Profile & Recalculate Goals'}
            </button>
          </div>
        </form>
      </div>

      {/* 3. Meal Reminders Configuration */}
      <div className="wellness-card" style={{ padding: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
              Meal Logging Reminders
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Configure gentle notification reminders for your daily meal slots
            </span>
          </div>
          {savedReminders && (
            <span className="badge badge-emerald">
              <Check size={14} /> Reminders Updated
            </span>
          )}
        </div>

        <form onSubmit={handleSaveReminders} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            
            {/* Breakfast */}
            <div style={{ background: '#0D1B2A', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid #263B55' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ fontSize: '0.88rem', fontWeight: '700', color: '#F8FAFC' }}>🌅 Breakfast</span>
                <input
                  type="checkbox"
                  checked={breakfastEnabled}
                  onChange={(e) => setBreakfastEnabled(e.target.checked)}
                  style={{ accentColor: '#38BDF8', width: '16px', height: '16px', cursor: 'pointer' }}
                />
              </div>
              <input
                type="time"
                value={breakfastTime}
                onChange={(e) => setBreakfastTime(e.target.value)}
                style={{
                  width: '100%',
                  background: '#F8FAFC',
                  color: '#0F172A',
                  WebkitTextFillColor: '#0F172A',
                  border: '1px solid #334155',
                  borderRadius: 'var(--radius-md)',
                  padding: '10px 14px',
                  fontSize: '0.94rem',
                  fontWeight: '700',
                  outline: 'none',
                  colorScheme: 'light',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                  transition: 'border-color 0.16s ease'
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#38BDF8'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = '#334155'; }}
              />
            </div>

            {/* Lunch */}
            <div style={{ background: '#0D1B2A', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid #263B55' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ fontSize: '0.88rem', fontWeight: '700', color: '#F8FAFC' }}>☀️ Lunch</span>
                <input
                  type="checkbox"
                  checked={lunchEnabled}
                  onChange={(e) => setLunchEnabled(e.target.checked)}
                  style={{ accentColor: '#38BDF8', width: '16px', height: '16px', cursor: 'pointer' }}
                />
              </div>
              <input
                type="time"
                value={lunchTime}
                onChange={(e) => setLunchTime(e.target.value)}
                style={{
                  width: '100%',
                  background: '#F8FAFC',
                  color: '#0F172A',
                  WebkitTextFillColor: '#0F172A',
                  border: '1px solid #334155',
                  borderRadius: 'var(--radius-md)',
                  padding: '10px 14px',
                  fontSize: '0.94rem',
                  fontWeight: '700',
                  outline: 'none',
                  colorScheme: 'light',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                  transition: 'border-color 0.16s ease'
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#38BDF8'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = '#334155'; }}
              />
            </div>

            {/* Snack */}
            <div style={{ background: '#0D1B2A', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid #263B55' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ fontSize: '0.88rem', fontWeight: '700', color: '#F8FAFC' }}>☕ Evening Snack</span>
                <input
                  type="checkbox"
                  checked={snackEnabled}
                  onChange={(e) => setSnackEnabled(e.target.checked)}
                  style={{ accentColor: '#38BDF8', width: '16px', height: '16px', cursor: 'pointer' }}
                />
              </div>
              <input
                type="time"
                value={snackTime}
                onChange={(e) => setSnackTime(e.target.value)}
                style={{
                  width: '100%',
                  background: '#F8FAFC',
                  color: '#0F172A',
                  WebkitTextFillColor: '#0F172A',
                  border: '1px solid #334155',
                  borderRadius: 'var(--radius-md)',
                  padding: '10px 14px',
                  fontSize: '0.94rem',
                  fontWeight: '700',
                  outline: 'none',
                  colorScheme: 'light',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                  transition: 'border-color 0.16s ease'
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#38BDF8'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = '#334155'; }}
              />
            </div>

            {/* Dinner */}
            <div style={{ background: '#0D1B2A', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid #263B55' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ fontSize: '0.88rem', fontWeight: '700', color: '#F8FAFC' }}>🌙 Dinner</span>
                <input
                  type="checkbox"
                  checked={dinnerEnabled}
                  onChange={(e) => setDinnerEnabled(e.target.checked)}
                  style={{ accentColor: '#38BDF8', width: '16px', height: '16px', cursor: 'pointer' }}
                />
              </div>
              <input
                type="time"
                value={dinnerTime}
                onChange={(e) => setDinnerTime(e.target.value)}
                style={{
                  width: '100%',
                  background: '#F8FAFC',
                  color: '#0F172A',
                  WebkitTextFillColor: '#0F172A',
                  border: '1px solid #334155',
                  borderRadius: 'var(--radius-md)',
                  padding: '10px 14px',
                  fontSize: '0.94rem',
                  fontWeight: '700',
                  outline: 'none',
                  colorScheme: 'light',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                  transition: 'border-color 0.16s ease'
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#38BDF8'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = '#334155'; }}
              />
            </div>

          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
            <button type="submit" disabled={savingReminders} className="btn-primary" style={{ padding: '10px 22px' }}>
              {savingReminders ? 'Saving Reminders...' : 'Save Reminder Schedules'}
            </button>
          </div>
        </form>
      </div>

    </div>
  );
};
