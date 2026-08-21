import React, { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { getToday } from '../utils/dateUtils';
import { ACTIVITY_TYPES, INTENSITY_LEVELS, calculateCaloriesBurned } from '../utils/activityConfig';
import { Activity, Clock, Flame, Calendar, X, Check, Loader2, Plus, Footprints, Navigation, FileText, ChevronDown, ChevronUp } from 'lucide-react';

export const ActivityModal = ({
  isOpen = true,
  onClose,
  onActivityLogged,
  onActivitySaved,
  defaultDate = null,
  editingActivity = null,
  initialData = null
}) => {
  const { profile } = useStore();

  const currentEditing = editingActivity || initialData;

  const [activityType, setActivityType] = useState('walking');
  const [duration, setDuration] = useState(30);
  const [intensity, setIntensity] = useState('moderate');
  const [date, setDate] = useState(defaultDate || getToday());
  const [time, setTime] = useState(() => {
    const now = new Date();
    return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  });
  const [steps, setSteps] = useState('');
  const [distanceKm, setDistanceKm] = useState('');
  const [notes, setNotes] = useState('');
  const [customCalories, setCustomCalories] = useState('');
  const [showOptionalFields, setShowOptionalFields] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    if (currentEditing) {
      setActivityType(currentEditing.type || currentEditing.activity_type || 'walking');
      setDuration(currentEditing.duration_min || currentEditing.duration_minutes || 30);
      setIntensity(currentEditing.intensity || 'moderate');
      if (currentEditing.calories_burned_est || currentEditing.calories_burned) {
        setCustomCalories(String(currentEditing.calories_burned || currentEditing.calories_burned_est));
      }
      if (currentEditing.date || currentEditing.recorded_at) {
        setDate((currentEditing.date || currentEditing.recorded_at).split('T')[0]);
      }
      if (currentEditing.time) {
        setTime(currentEditing.time);
      }
      if (currentEditing.steps) {
        setSteps(String(currentEditing.steps));
        setShowOptionalFields(true);
      }
      if (currentEditing.distance_km) {
        setDistanceKm(String(currentEditing.distance_km));
        setShowOptionalFields(true);
      }
      if (currentEditing.notes) {
        setNotes(currentEditing.notes);
        setShowOptionalFields(true);
      }
    } else if (defaultDate) {
      setDate(defaultDate);
    }
  }, [currentEditing, defaultDate]);

  if (!isOpen) return null;

  const userWeight = profile?.weight_kg || 70.0;
  const estimatedCalories = calculateCaloriesBurned(activityType, duration, intensity, userWeight);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg('');

    const parsedDuration = parseInt(duration, 10);
    if (!parsedDuration || parsedDuration <= 0) {
      setError('Please enter a valid duration greater than 0 minutes.');
      return;
    }

    if (steps && (parseInt(steps, 10) < 0 || isNaN(parseInt(steps, 10)))) {
      setError('Steps cannot be negative.');
      return;
    }

    if (distanceKm && (parseFloat(distanceKm) < 0 || isNaN(parseFloat(distanceKm)))) {
      setError('Distance cannot be negative.');
      return;
    }

    if (customCalories && (parseFloat(customCalories) < 0 || isNaN(parseFloat(customCalories)))) {
      setError('Calories burned cannot be negative.');
      return;
    }

    if (!date) {
      setError('Please provide a valid activity date.');
      return;
    }

    setLoading(true);
    try {
      const selectedTypeObj = ACTIVITY_TYPES.find(a => a.id === activityType);
      const payload = {
        type: activityType,
        activity_type: activityType,
        activity_name: selectedTypeObj?.label || 'Workout',
        duration_min: parsedDuration,
        duration_minutes: parsedDuration,
        intensity: intensity,
        calories_burned: customCalories ? parseFloat(customCalories) : estimatedCalories,
        calories_burned_est: customCalories ? parseFloat(customCalories) : estimatedCalories,
        steps: steps ? parseInt(steps, 10) : 0,
        distance_km: distanceKm ? parseFloat(distanceKm) : 0.0,
        notes: notes.trim(),
        date: date,
        time: time
      };

      let result;
      if (currentEditing && currentEditing.id) {
        result = await api.updateActivity(currentEditing.id, payload);
      } else {
        result = await api.logActivity(payload);
      }

      setSuccessMsg(currentEditing ? 'Activity updated successfully.' : 'Activity logged successfully.');
      
      if (onActivityLogged) onActivityLogged(result);
      if (onActivitySaved) onActivitySaved(result);
      
      setTimeout(() => {
        onClose();
      }, 350);
    } catch (err) {
      console.error('Failed to save physical activity:', err);
      setError(err.message || 'Unable to save activity. Please check your connection.');
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
        WebkitBackdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '16px'
      }}
      onClick={onClose}
    >
      <div
        className="wellness-card"
        style={{
          width: '100%',
          maxWidth: '540px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '28px',
          position: 'relative',
          background: 'var(--bg-card)',
          boxShadow: 'var(--shadow-xl)',
          border: '1px solid var(--border-glass)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px', height: '40px', borderRadius: '12px',
              background: 'var(--primary-light)',
              color: 'var(--primary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: 'var(--shadow-sm)'
            }}>
              <Activity size={22} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                {currentEditing ? 'Edit Physical Activity' : 'Log Physical Activity'}
              </h2>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Deterministic MET Energy Expenditure
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn-secondary"
            style={{
              borderRadius: '50%',
              width: '32px',
              height: '32px',
              padding: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <X size={16} />
          </button>
        </div>

        {error && (
          <div style={{
            background: 'var(--error-bg)',
            border: '1px solid rgba(217, 93, 93, 0.3)',
            color: 'var(--error-rose)',
            padding: '10px 14px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.85rem',
            marginBottom: '16px'
          }}>
            {error}
          </div>
        )}

        {successMsg && (
          <div style={{
            background: 'var(--primary-light)',
            border: '1px solid var(--primary-border)',
            color: 'var(--primary)',
            padding: '10px 14px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.85rem',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <Check size={16} /> {successMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          
          {/* 1. Activity Type Grid */}
          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.04em', marginBottom: '8px' }}>
              Activity Type
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(105px, 1fr))', gap: '8px' }}>
              {ACTIVITY_TYPES.map(act => {
                const isSelected = activityType === act.id;
                return (
                  <button
                    key={act.id}
                    type="button"
                    onClick={() => {
                      setActivityType(act.id);
                      if (!currentEditing) {
                        setDuration(act.defaultDuration || 30);
                      }
                    }}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '10px 8px',
                      borderRadius: '12px',
                      background: isSelected ? 'var(--primary-light)' : 'var(--bg-subtle)',
                      border: `1.5px solid ${isSelected ? 'var(--primary)' : 'var(--border-glass)'}`,
                      color: isSelected ? 'var(--primary)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <span style={{ fontSize: '1.35rem' }}>{act.icon}</span>
                    <span style={{ fontSize: '0.75rem', fontWeight: isSelected ? '800' : '600', textAlign: 'center', lineHeight: 1.1 }}>
                      {act.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. Duration (Minutes) */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label style={{ fontSize: '0.78rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
                Duration (Minutes)
              </label>
              <div style={{ display: 'flex', gap: '6px' }}>
                {[15, 30, 45, 60].map(m => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setDuration(m)}
                    className="btn-secondary"
                    style={{
                      padding: '2px 8px',
                      fontSize: '0.72rem',
                      borderRadius: '6px',
                      background: duration === m ? 'var(--primary-light)' : 'transparent',
                      color: duration === m ? 'var(--primary)' : 'var(--text-muted)',
                      borderColor: duration === m ? 'var(--primary)' : 'var(--border-glass)'
                    }}
                  >
                    +{m}m
                  </button>
                ))}
              </div>
            </div>
            <div style={{ position: 'relative' }}>
              <Clock size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '14px', top: '13px' }} />
              <input
                type="number"
                min="1"
                max="1440"
                className="input-field"
                style={{ paddingLeft: '40px' }}
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                required
              />
            </div>
          </div>

          {/* 3. Intensity */}
          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.04em', marginBottom: '8px' }}>
              Intensity Level
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
              {INTENSITY_LEVELS.map(lvl => {
                const isSelected = intensity === lvl.id;
                return (
                  <button
                    key={lvl.id}
                    type="button"
                    onClick={() => setIntensity(lvl.id)}
                    style={{
                      padding: '10px 8px',
                      borderRadius: '10px',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '2px',
                      background: isSelected ? 'var(--primary-light)' : 'var(--bg-subtle)',
                      border: `1.5px solid ${isSelected ? 'var(--primary)' : 'var(--border-glass)'}`,
                      color: isSelected ? 'var(--primary)' : 'var(--text-secondary)',
                      cursor: 'pointer'
                    }}
                  >
                    <span style={{ fontSize: '0.85rem', fontWeight: '700' }}>{lvl.label}</span>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textAlign: 'center', lineHeight: 1.1 }}>
                      {lvl.description.split(',')[0]}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 4. Live Estimated Burn Banner */}
          <div style={{
            background: 'var(--primary-light)',
            border: '1px solid var(--primary-border)',
            borderRadius: 'var(--radius-md)',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Estimated Energy Burned
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: '900', color: 'var(--primary)' }}>
                {customCalories ? parseFloat(customCalories) || 0 : estimatedCalories} <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>kcal</span>
              </div>
            </div>
            <div style={{ textAlign: 'right', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Based on {userWeight}kg body weight<br />
              MET formula calibrated
            </div>
          </div>

          {/* 5. Date & Time Row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Date
              </label>
              <input
                type="date"
                className="input-field"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Time
              </label>
              <input
                type="time"
                className="input-field"
                value={time}
                onChange={(e) => setTime(e.target.value)}
              />
            </div>
          </div>

          {/* 6. Expandable Optional Fields (Steps, Distance, Notes, Custom Calories) */}
          <div>
            <button
              type="button"
              onClick={() => setShowOptionalFields(!showOptionalFields)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--primary)',
                fontSize: '0.82rem',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                cursor: 'pointer',
                padding: '4px 0'
              }}
            >
              <span>{showOptionalFields ? 'Hide optional metrics' : '+ Add steps, distance, notes, or custom calories'}</span>
              {showOptionalFields ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {showOptionalFields && (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                marginTop: '10px',
                padding: '14px',
                background: 'var(--bg-subtle)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-glass)'
              }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      Steps (optional)
                    </label>
                    <div style={{ position: 'relative' }}>
                      <Footprints size={15} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
                      <input
                        type="number"
                        min="0"
                        placeholder="e.g. 5000"
                        className="input-field"
                        style={{ paddingLeft: '36px' }}
                        value={steps}
                        onChange={(e) => setSteps(e.target.value)}
                      />
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      Distance in km (optional)
                    </label>
                    <div style={{ position: 'relative' }}>
                      <Navigation size={15} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="e.g. 3.5"
                        className="input-field"
                        style={{ paddingLeft: '36px' }}
                        value={distanceKm}
                        onChange={(e) => setDistanceKm(e.target.value)}
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Custom Calories Burned Override (optional)
                  </label>
                  <input
                    type="number"
                    min="0"
                    placeholder={`Leave blank to use estimated ${estimatedCalories} kcal`}
                    className="input-field"
                    value={customCalories}
                    onChange={(e) => setCustomCalories(e.target.value)}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Notes (optional)
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Workout details, pace, feeling..."
                    className="input-field"
                    style={{ resize: 'vertical' }}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Submit and Cancel Buttons */}
          <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              style={{ flex: 1, padding: '12px' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
              style={{ flex: 2, padding: '12px' }}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Check size={16} />
                  <span>{currentEditing ? 'Update Activity' : 'Save Activity'}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
