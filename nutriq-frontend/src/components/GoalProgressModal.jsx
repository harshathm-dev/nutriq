import React, { useState, useEffect } from 'react';
import {
  X, Target, TrendingDown, TrendingUp, Calendar, AlertTriangle,
  Scale, CheckCircle2, Flame, Sparkles, RefreshCw, Clock, ArrowRight, ShieldCheck
} from 'lucide-react';
import { api } from '../services/api';

export const GoalProgressModal = ({
  isOpen,
  onClose,
  progressData,
  onGoalUpdated
}) => {
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'update_weight' | 'edit_goal'
  const [weightHistory, setWeightHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Update Weight Form State
  const [inputWeight, setInputWeight] = useState('');
  const [inputWeightDate, setInputWeightDate] = useState(new Date().toISOString().split('T')[0]);
  const [savingWeight, setSavingWeight] = useState(false);
  const [weightMsg, setWeightMsg] = useState('');

  // Edit Goal Form State
  const [goalType, setGoalType] = useState('weight_loss');
  const [targetWeight, setTargetWeight] = useState('');
  const [desiredRate, setDesiredRate] = useState(0.5);
  const [savingGoal, setSavingGoal] = useState(false);
  const [goalMsg, setGoalMsg] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchWeightHistory();
      if (progressData) {
        setInputWeight(progressData.current_weight_kg || '');
        setGoalType(progressData.goal_type || 'weight_loss');
        setTargetWeight(progressData.target_weight_kg || '');
        setDesiredRate(progressData.weekly_pace_kg || 0.5);
      }
    }
  }, [isOpen, progressData]);

  const fetchWeightHistory = async () => {
    setLoadingHistory(true);
    try {
      const history = await api.getWeightHistory();
      setWeightHistory(history || []);
    } catch (e) {
      console.warn("Could not fetch weight history:", e);
    } finally {
      setLoadingHistory(false);
    }
  };

  if (!isOpen) return null;

  const currentWt = progressData?.current_weight_kg || 70;
  const targetWt = progressData?.target_weight_kg || 65;
  const startWt = progressData?.starting_weight_kg || currentWt;
  const remainingWt = progressData?.weight_remaining_kg || Math.abs(currentWt - targetWt);
  const progressPct = progressData?.progress_percentage || 0;
  const weeklyPace = progressData?.weekly_pace_kg || 0.5;
  const estDate = progressData?.estimated_target_date || 'In Progress';
  const calorieTarget = progressData?.calorie_target || 2000;
  const tdee = progressData?.tdee || 2200;
  const bmr = progressData?.bmr || 1650;

  // Dynamic preview calculation for Edit Goal tab
  const previewTargetWeight = parseFloat(targetWeight) || currentWt;
  const previewPace = parseFloat(desiredRate) || 0.5;
  const previewRemaining = Math.abs(currentWt - previewTargetWeight);
  const previewWeeks = previewPace > 0 ? Math.round(previewRemaining / previewPace) : 0;
  const previewTargetDate = new Date();
  previewTargetDate.setDate(previewTargetDate.getDate() + (previewWeeks * 7));
  const previewDateStr = previewTargetDate.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

  const handleLogWeightSubmit = async (e) => {
    e.preventDefault();
    const wtNum = parseFloat(inputWeight);
    if (!wtNum || wtNum < 20 || wtNum > 350) {
      setWeightMsg('Please enter a valid weight between 20 and 350 kg.');
      return;
    }
    setSavingWeight(true);
    setWeightMsg('');
    try {
      const timestamp = new Date(inputWeightDate).toISOString();
      await api.recordWeight(wtNum, timestamp);
      setWeightMsg('Weight logged successfully!');
      await fetchWeightHistory();
      if (onGoalUpdated) await onGoalUpdated();
      setTimeout(() => {
        setWeightMsg('');
        setActiveTab('overview');
      }, 1200);
    } catch (err) {
      setWeightMsg(err.message || 'Failed to log weight');
    } finally {
      setSavingWeight(false);
    }
  };

  const handleEditGoalSubmit = async (e) => {
    e.preventDefault();
    const targetWtNum = parseFloat(targetWeight);
    if (!targetWtNum || targetWtNum < 20 || targetWtNum > 350) {
      setGoalMsg('Please enter a valid target weight between 20 and 350 kg.');
      return;
    }
    setSavingGoal(true);
    setGoalMsg('');
    try {
      await api.createGoal({
        goal_type: goalType,
        current_weight_kg: currentWt,
        target_weight_kg: targetWtNum,
        desired_rate: parseFloat(desiredRate) || 0.5
      });
      setGoalMsg('Goal updated successfully!');
      if (onGoalUpdated) await onGoalUpdated();
      setTimeout(() => {
        setGoalMsg('');
        setActiveTab('overview');
      }, 1200);
    } catch (err) {
      setGoalMsg(err.message || 'Failed to update goal');
    } finally {
      setSavingGoal(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(23, 35, 31, 0.45)',
        backdropFilter: 'blur(6px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '680px',
          maxHeight: '90vh',
          overflowY: 'auto',
          borderRadius: '20px',
          padding: '28px 32px',
          background: 'var(--goal-bg, #F7FAF8)',
          border: '1px solid var(--goal-border, #D5E2DC)',
          boxShadow: '0 12px 40px rgba(23, 35, 31, 0.12)',
          position: 'relative'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '12px',
              background: 'var(--goal-light-green, #E4F6EE)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(22, 134, 95, 0.2)'
            }}>
              <Target size={22} color="var(--goal-primary, #16865F)" />
            </div>
            <div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: '800', margin: 0, color: 'var(--goal-text-primary, #17231F)' }}>
                Goal Progress & Weight Projection
              </h2>
              <p style={{ color: 'var(--goal-text-secondary, #52635D)', fontSize: '0.84rem', margin: 0 }}>
                Detailed tracking and healthy pace projection based on your profile
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            style={{
              background: '#FFFFFF',
              border: '1px solid #CBD8D2',
              color: '#52635D',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 0.15s ease, color 0.15s ease'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = '#EAF4EF';
              e.currentTarget.style.color = '#17231F';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = '#FFFFFF';
              e.currentTarget.style.color = '#52635D';
            }}
            title="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Navigation Pills */}
        <div style={{
          display: 'flex',
          gap: '6px',
          padding: '4px',
          background: 'var(--goal-surface, #FFFFFF)',
          borderRadius: '12px',
          marginBottom: '20px',
          border: '1px solid var(--goal-border, #D5E2DC)'
        }}>
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            style={{
              flex: 1,
              padding: '9px 14px',
              borderRadius: '8px',
              background: activeTab === 'overview' ? 'var(--goal-bright-green, #19B77A)' : 'transparent',
              color: activeTab === 'overview' ? '#FFFFFF' : 'var(--goal-text-secondary, #52635D)',
              fontWeight: activeTab === 'overview' ? '700' : '600',
              fontSize: '0.85rem',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={e => {
              if (activeTab !== 'overview') {
                e.currentTarget.style.background = 'var(--goal-light-green, #E4F6EE)';
                e.currentTarget.style.color = 'var(--goal-primary, #16865F)';
              }
            }}
            onMouseLeave={e => {
              if (activeTab !== 'overview') {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = 'var(--goal-text-secondary, #52635D)';
              }
            }}
          >
            Goal Overview
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('update_weight')}
            style={{
              flex: 1,
              padding: '9px 14px',
              borderRadius: '8px',
              background: activeTab === 'update_weight' ? 'var(--goal-bright-green, #19B77A)' : 'transparent',
              color: activeTab === 'update_weight' ? '#FFFFFF' : 'var(--goal-text-secondary, #52635D)',
              fontWeight: activeTab === 'update_weight' ? '700' : '600',
              fontSize: '0.85rem',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={e => {
              if (activeTab !== 'update_weight') {
                e.currentTarget.style.background = 'var(--goal-light-green, #E4F6EE)';
                e.currentTarget.style.color = 'var(--goal-primary, #16865F)';
              }
            }}
            onMouseLeave={e => {
              if (activeTab !== 'update_weight') {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = 'var(--goal-text-secondary, #52635D)';
              }
            }}
          >
            + Update Weight
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('edit_goal')}
            style={{
              flex: 1,
              padding: '9px 14px',
              borderRadius: '8px',
              background: activeTab === 'edit_goal' ? 'var(--goal-bright-green, #19B77A)' : 'transparent',
              color: activeTab === 'edit_goal' ? '#FFFFFF' : 'var(--goal-text-secondary, #52635D)',
              fontWeight: activeTab === 'edit_goal' ? '700' : '600',
              fontSize: '0.85rem',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={e => {
              if (activeTab !== 'edit_goal') {
                e.currentTarget.style.background = 'var(--goal-light-green, #E4F6EE)';
                e.currentTarget.style.color = 'var(--goal-primary, #16865F)';
              }
            }}
            onMouseLeave={e => {
              if (activeTab !== 'edit_goal') {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = 'var(--goal-text-secondary, #52635D)';
              }
            }}
          >
            Edit Goal & Pace
          </button>
        </div>

        {/* TAB 1: OVERVIEW */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            {/* Weight Journey Card */}
            <div style={{
              background: 'var(--goal-surface, #FFFFFF)',
              border: '1px solid var(--goal-border, #D5E2DC)',
              borderRadius: '16px',
              padding: '20px',
              boxShadow: '0 4px 18px rgba(23, 35, 31, 0.06)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--goal-text-secondary, #52635D)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Weight Journey
                </span>
                <span style={{
                  fontSize: '0.78rem',
                  padding: '4px 10px',
                  borderRadius: '8px',
                  background: 'var(--goal-light-green, #E4F6EE)',
                  color: 'var(--goal-primary, #16865F)',
                  fontWeight: '700'
                }}>
                  {progressPct}% Completed
                </span>
              </div>

              {/* Progress Bar */}
              <div style={{ height: '10px', background: '#E3EBE7', borderRadius: '9999px', overflow: 'hidden', marginBottom: '16px' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${Math.min(100, Math.max(2, progressPct))}%`,
                    background: 'var(--goal-bright-green, #19B77A)',
                    borderRadius: '9999px',
                    transition: 'width 0.4s ease'
                  }}
                />
              </div>

              {/* Trajectory Checkpoints */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.84rem' }}>
                <div>
                  <span style={{ color: 'var(--goal-text-muted, #71817B)', fontSize: '0.75rem', display: 'block', marginBottom: '2px' }}>Start</span>
                  <div style={{ fontWeight: '800', color: 'var(--goal-text-primary, #17231F)', fontSize: '1rem' }}>{startWt} kg</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <span style={{ color: 'var(--goal-text-muted, #71817B)', fontSize: '0.75rem', fontWeight: '700', display: 'block', marginBottom: '2px' }}>Current</span>
                  <div style={{ fontWeight: '900', color: 'var(--goal-primary, #16865F)', fontSize: '1.15rem' }}>{currentWt} kg</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ color: 'var(--goal-text-muted, #71817B)', fontSize: '0.75rem', display: 'block', marginBottom: '2px' }}>Target Goal</span>
                  <div style={{ fontWeight: '800', color: 'var(--goal-blue, #2589D8)', fontSize: '1rem' }}>{targetWt} kg</div>
                </div>
              </div>
            </div>

            {/* Core Statistics Cards Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(135px, 1fr))',
              gap: '12px'
            }}>
              <div style={{
                background: 'var(--goal-surface, #FFFFFF)',
                padding: '16px',
                borderRadius: '14px',
                border: '1px solid var(--goal-border, #D5E2DC)',
                boxShadow: '0 2px 10px rgba(23, 35, 31, 0.04)'
              }}>
                <div style={{ fontSize: '0.74rem', color: 'var(--goal-text-secondary, #52635D)', fontWeight: '600' }}>Remaining to Goal</div>
                <div style={{ fontSize: '1.3rem', fontWeight: '800', color: 'var(--goal-orange, #F28C28)', marginTop: '4px' }}>
                  {remainingWt} <span style={{ fontSize: '0.8rem', fontWeight: '600' }}>kg</span>
                </div>
              </div>

              <div style={{
                background: 'var(--goal-surface, #FFFFFF)',
                padding: '16px',
                borderRadius: '14px',
                border: '1px solid var(--goal-border, #D5E2DC)',
                boxShadow: '0 2px 10px rgba(23, 35, 31, 0.04)'
              }}>
                <div style={{ fontSize: '0.74rem', color: 'var(--goal-text-secondary, #52635D)', fontWeight: '600' }}>Weekly Pace</div>
                <div style={{ fontSize: '1.3rem', fontWeight: '800', color: '#19A974', marginTop: '4px' }}>
                  {weeklyPace} <span style={{ fontSize: '0.8rem', fontWeight: '600' }}>kg/week</span>
                </div>
              </div>

              <div style={{
                background: 'var(--goal-surface, #FFFFFF)',
                padding: '16px',
                borderRadius: '14px',
                border: '1px solid var(--goal-border, #D5E2DC)',
                boxShadow: '0 2px 10px rgba(23, 35, 31, 0.04)'
              }}>
                <div style={{ fontSize: '0.74rem', color: 'var(--goal-text-secondary, #52635D)', fontWeight: '600' }}>Est. Target Date</div>
                <div style={{ fontSize: '1.15rem', fontWeight: '800', color: 'var(--goal-blue, #2589D8)', marginTop: '5px' }}>
                  {estDate}
                </div>
              </div>

              <div style={{
                background: 'var(--goal-surface, #FFFFFF)',
                padding: '16px',
                borderRadius: '14px',
                border: '1px solid var(--goal-border, #D5E2DC)',
                boxShadow: '0 2px 10px rgba(23, 35, 31, 0.04)'
              }}>
                <div style={{ fontSize: '0.74rem', color: 'var(--goal-text-secondary, #52635D)', fontWeight: '600' }}>Daily Calorie Target</div>
                <div style={{ fontSize: '1.3rem', fontWeight: '800', color: 'var(--goal-primary, #16865F)', marginTop: '4px' }}>
                  {Math.round(calorieTarget)} <span style={{ fontSize: '0.8rem', fontWeight: '600' }}>kcal</span>
                </div>
              </div>
            </div>

            {/* Safe Weight Loss Recommendation Banner */}
            {weeklyPace > 1.0 ? (
              <div style={{
                background: '#FDF2F2',
                border: '1px solid #F8B4B4',
                borderRadius: '14px',
                padding: '14px 18px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px'
              }}>
                <AlertTriangle size={20} color="var(--goal-danger, #DC5A5A)" style={{ flexShrink: 0, marginTop: '2px' }} />
                <div style={{ fontSize: '0.84rem', color: 'var(--goal-text-secondary, #52635D)', lineHeight: 1.45 }}>
                  <strong style={{ color: 'var(--goal-danger, #DC5A5A)' }}>Aggressive Pace Notice:</strong> A rate of {weeklyPace} kg/week may cause muscle loss and fatigue. A sustainable pace of 0.5–0.75 kg/week is recommended for lasting results.
                </div>
              </div>
            ) : (
              <div style={{
                background: '#EAF8F2',
                border: '1px solid #B9E6D0',
                borderRadius: '14px',
                padding: '14px 18px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px'
              }}>
                <ShieldCheck size={20} color="var(--goal-primary, #16865F)" style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div style={{ fontSize: '0.95rem', fontWeight: '800', color: 'var(--goal-primary, #16865F)', marginBottom: '2px' }}>
                    ✓ Healthy & Sustainable Pace
                  </div>
                  <div style={{ fontSize: '0.84rem', color: 'var(--goal-text-secondary, #52635D)', lineHeight: 1.45 }}>
                    Your pace of {weeklyPace} kg/week is within the safe 0.5–0.75 kg/week window, preserving lean muscle mass and energy levels.
                  </div>
                </div>
              </div>
            )}

            {/* Weight Log History */}
            <div>
              <h4 style={{ fontSize: '1rem', fontWeight: '700', marginBottom: '10px', color: 'var(--goal-text-primary, #17231F)' }}>
                Recent Weight Entries ({weightHistory.length})
              </h4>
              {loadingHistory ? (
                <div style={{ textAlign: 'center', padding: '16px', color: 'var(--goal-text-muted, #71817B)' }}>
                  Loading history...
                </div>
              ) : weightHistory.length === 0 ? (
                <div style={{
                  textAlign: 'center',
                  padding: '24px',
                  background: 'var(--goal-surface, #FFFFFF)',
                  borderRadius: '12px',
                  border: '1px dashed #B8C9C1'
                }}>
                  <p style={{ color: 'var(--goal-text-secondary, #52635D)', fontSize: '0.86rem', margin: 0 }}>
                    No recorded weight entries yet. Use "+ Update Weight" to log your current weight.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '8px', maxHeight: '160px', overflowY: 'auto' }}>
                  {weightHistory.slice().reverse().map((entry) => (
                    <div
                      key={entry.id}
                      style={{
                        background: 'var(--goal-surface, #FFFFFF)',
                        border: '1px solid var(--goal-border, #D5E2DC)',
                        borderRadius: '10px',
                        padding: '10px 14px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <span style={{ fontSize: '0.8rem', color: 'var(--goal-text-secondary, #52635D)', fontWeight: '600' }}>
                        {new Date(entry.recorded_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                      </span>
                      <span style={{ fontSize: '0.95rem', fontWeight: '800', color: 'var(--goal-primary, #16865F)' }}>
                        {entry.weight_kg} kg
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: UPDATE WEIGHT FORM */}
        {activeTab === 'update_weight' && (
          <form onSubmit={handleLogWeightSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{
              background: 'var(--goal-light-green, #EAF8F2)',
              padding: '14px 16px',
              borderRadius: '12px',
              border: '1px solid var(--goal-border, #B9E6D0)'
            }}>
              <h4 style={{ margin: '0 0 4px 0', fontSize: '0.92rem', color: 'var(--goal-primary, #16865F)', fontWeight: '700' }}>Log Your Current Weight</h4>
              <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--goal-text-secondary, #52635D)' }}>
                Logging your weight updates your goal progress, daily calorie targets, and activity streak.
              </p>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: '700', marginBottom: '6px', color: 'var(--goal-text-secondary, #52635D)' }}>
                Weight (kg) *
              </label>
              <input
                type="number"
                step="0.1"
                min="20"
                max="350"
                placeholder="e.g. 74.5"
                value={inputWeight}
                onChange={(e) => setInputWeight(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  border: '1px solid var(--goal-border, #D5E2DC)',
                  background: 'var(--goal-surface, #FFFFFF)',
                  color: 'var(--goal-text-primary, #17231F)',
                  fontSize: '1.05rem',
                  fontWeight: '700',
                  outline: 'none'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: '700', marginBottom: '6px', color: 'var(--goal-text-secondary, #52635D)' }}>
                Date Recorded
              </label>
              <input
                type="date"
                value={inputWeightDate}
                onChange={(e) => setInputWeightDate(e.target.value)}
                max={new Date().toISOString().split('T')[0]}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  border: '1px solid var(--goal-border, #D5E2DC)',
                  background: 'var(--goal-surface, #FFFFFF)',
                  color: 'var(--goal-text-primary, #17231F)',
                  fontSize: '0.92rem',
                  fontWeight: '600',
                  outline: 'none'
                }}
              />
            </div>

            {weightMsg && (
              <div style={{
                padding: '10px 14px',
                borderRadius: '10px',
                fontSize: '0.84rem',
                fontWeight: '600',
                background: weightMsg.includes('success') ? 'var(--goal-light-green, #EAF8F2)' : 'var(--error-bg, #FDF2F2)',
                color: weightMsg.includes('success') ? 'var(--goal-primary, #16865F)' : 'var(--goal-danger, #DC5A5A)',
                border: `1px solid ${weightMsg.includes('success') ? 'var(--goal-border, #B9E6D0)' : 'var(--error-rose-light, #F8B4B4)'}`
              }}>
                {weightMsg}
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
              <button
                type="button"
                onClick={() => setActiveTab('overview')}
                style={{
                  flex: 1,
                  padding: '10px 18px',
                  borderRadius: '10px',
                  background: 'var(--goal-surface, #FFFFFF)',
                  border: '1px solid var(--goal-border, #CBD8D2)',
                  color: 'var(--goal-text-secondary, #52635D)',
                  fontWeight: '600',
                  fontSize: '0.85rem',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingWeight}
                style={{
                  flex: 2,
                  padding: '10px 18px',
                  borderRadius: '10px',
                  background: 'var(--goal-bright-green, #19B77A)',
                  color: '#FFFFFF',
                  fontWeight: '700',
                  fontSize: '0.85rem',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                {savingWeight ? 'Logging...' : 'Save & Update Weight'}
              </button>
            </div>
          </form>
        )}

        {/* TAB 3: EDIT GOAL & PACE FORM */}
        {activeTab === 'edit_goal' && (
          <form onSubmit={handleEditGoalSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: '700', marginBottom: '6px', color: 'var(--goal-text-secondary, #52635D)' }}>
                Goal Type
              </label>
              <select
                value={goalType}
                onChange={(e) => setGoalType(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  border: '1px solid var(--goal-border, #D5E2DC)',
                  background: 'var(--goal-surface, #FFFFFF)',
                  color: 'var(--goal-text-primary, #17231F)',
                  fontSize: '0.92rem',
                  fontWeight: '600',
                  outline: 'none'
                }}
              >
                <option value="weight_loss">Weight Loss (Fat Loss)</option>
                <option value="maintain">Maintain Current Weight</option>
                <option value="muscle_building">Muscle Building / Hypertrophy</option>
                <option value="weight_gain">Healthy Weight Gain</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.84rem', fontWeight: '700', marginBottom: '6px', color: 'var(--goal-text-secondary, #52635D)' }}>
                Target Weight (kg) *
              </label>
              <input
                type="number"
                step="0.5"
                min="20"
                max="350"
                placeholder="e.g. 68.0"
                value={targetWeight}
                onChange={(e) => setTargetWeight(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  border: '1px solid var(--goal-border, #D5E2DC)',
                  background: 'var(--goal-surface, #FFFFFF)',
                  color: 'var(--goal-text-primary, #17231F)',
                  fontSize: '1.05rem',
                  fontWeight: '700',
                  outline: 'none'
                }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label style={{ fontSize: '0.84rem', fontWeight: '700', color: 'var(--goal-text-secondary, #52635D)' }}>
                  Preferred Weekly Pace: <strong style={{ color: 'var(--goal-primary, #16865F)' }}>{desiredRate} kg/week</strong>
                </label>
                <span style={{ fontSize: '0.74rem', color: 'var(--goal-text-muted, #71817B)', fontWeight: '600' }}>
                  Recommended: 0.5 kg/wk
                </span>
              </div>
              <input
                type="range"
                min="0.2"
                max="1.5"
                step="0.1"
                value={desiredRate}
                onChange={(e) => setDesiredRate(parseFloat(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--goal-bright-green, #19B77A)', cursor: 'pointer' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--goal-text-muted, #71817B)', marginTop: '4px' }}>
                <span>0.2 kg/wk (Gentle)</span>
                <span>0.5 kg/wk (Optimal)</span>
                <span>1.0 kg/wk (Fast)</span>
                <span>1.5 kg/wk (Aggressive)</span>
              </div>
            </div>

            {/* Live Projection Preview Box */}
            <div style={{
              background: 'var(--goal-surface, #FFFFFF)',
              border: '1px solid var(--goal-border, #D5E2DC)',
              borderRadius: '14px',
              padding: '16px',
              boxShadow: '0 2px 10px rgba(23, 35, 31, 0.04)'
            }}>
              <div style={{ fontSize: '0.76rem', color: 'var(--goal-text-secondary, #52635D)', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '10px' }}>
                Live Goal Projection Preview
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem', color: 'var(--goal-text-secondary, #52635D)' }}>
                <span>Total weight change:</span>
                <strong style={{ color: 'var(--goal-orange, #F28C28)', fontWeight: '800' }}>{previewRemaining.toFixed(1)} kg</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem', color: 'var(--goal-text-secondary, #52635D)', marginTop: '6px' }}>
                <span>Estimated duration:</span>
                <strong style={{ color: 'var(--goal-blue, #2589D8)', fontWeight: '800' }}>~{previewWeeks} weeks</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem', color: 'var(--goal-text-secondary, #52635D)', marginTop: '6px' }}>
                <span>Estimated completion:</span>
                <strong style={{ color: 'var(--goal-primary, #16865F)', fontWeight: '800' }}>{previewDateStr}</strong>
              </div>
            </div>

            {desiredRate > 1.0 && (
              <div style={{ padding: '10px 14px', borderRadius: '10px', fontSize: '0.82rem', background: 'var(--error-bg, #FDF2F2)', color: 'var(--goal-danger, #DC5A5A)', border: '1px solid var(--error-rose-light, #F8B4B4)' }}>
                ⚠️ <strong>Note:</strong> Selecting a pace over 1.0 kg/week is aggressive. Slower weight change is easier to maintain long-term.
              </div>
            )}

            {goalMsg && (
              <div style={{
                padding: '10px 14px',
                borderRadius: '10px',
                fontSize: '0.84rem',
                fontWeight: '600',
                background: goalMsg.includes('success') ? 'var(--goal-light-green, #EAF8F2)' : 'var(--error-bg, #FDF2F2)',
                color: goalMsg.includes('success') ? 'var(--goal-primary, #16865F)' : 'var(--goal-danger, #DC5A5A)',
                border: `1px solid ${goalMsg.includes('success') ? 'var(--goal-border, #B9E6D0)' : 'var(--error-rose-light, #F8B4B4)'}`
              }}>
                {goalMsg}
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
              <button
                type="button"
                onClick={() => setActiveTab('overview')}
                style={{
                  flex: 1,
                  padding: '10px 18px',
                  borderRadius: '10px',
                  background: 'var(--goal-surface, #FFFFFF)',
                  border: '1px solid var(--goal-border, #CBD8D2)',
                  color: 'var(--goal-text-secondary, #52635D)',
                  fontWeight: '600',
                  fontSize: '0.85rem',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingGoal}
                style={{
                  flex: 2,
                  padding: '10px 18px',
                  borderRadius: '10px',
                  background: 'var(--goal-bright-green, #19B77A)',
                  color: '#FFFFFF',
                  fontWeight: '700',
                  fontSize: '0.85rem',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                {savingGoal ? 'Saving...' : 'Save New Goal'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default GoalProgressModal;
