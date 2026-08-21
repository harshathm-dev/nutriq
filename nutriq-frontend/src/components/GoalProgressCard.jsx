import React, { useState, useEffect } from 'react';
import { Target, TrendingDown, TrendingUp, Calendar, ChevronRight, Scale, AlertTriangle } from 'lucide-react';
import { GoalProgressModal } from './GoalProgressModal';
import { api } from '../services/api';

export const GoalProgressCard = ({ onGoalUpdated }) => {
  const [progressData, setProgressData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    fetchProgress();
  }, []);

  const fetchProgress = async () => {
    setLoading(true);
    try {
      const data = await api.getGoalProgress();
      if (data) setProgressData(data);
    } catch (e) {
      console.warn("Could not fetch goal progress:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleGoalOrWeightUpdated = async () => {
    await fetchProgress();
    if (onGoalUpdated) await onGoalUpdated();
  };

  const currentWt = progressData?.current_weight_kg || 80;
  const targetWt = progressData?.target_weight_kg || 75;
  const startWt = progressData?.starting_weight_kg || currentWt;
  const remainingWt = progressData?.weight_remaining_kg || Math.abs(currentWt - targetWt);
  const progressPct = progressData?.progress_percentage || 0;
  const weeklyPace = progressData?.weekly_pace_kg || 0.5;
  const estDate = progressData?.estimated_target_date || 'In Progress';
  const goalType = progressData?.goal_type || 'weight_loss';
  const isAggressive = progressData?.is_pace_aggressive;

  const goalLabel = goalType === 'weight_loss' ? 'Weight Loss'
    : goalType === 'muscle_building' ? 'Muscle Building'
    : goalType === 'weight_gain' ? 'Weight Gain'
    : 'Maintain Weight';

  return (
    <>
      <div
        className="wellness-card wellness-card-interactive"
        onClick={() => setShowModal(true)}
        style={{
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          gap: '16px',
          height: '100%',
          cursor: 'pointer'
        }}
      >
        {/* Top Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'var(--goal-light-green, #E4F6EE)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(22, 134, 95, 0.2)'
            }}>
              <Target size={22} color="var(--goal-primary, #16865F)" />
            </div>
            <div>
              <span style={{ fontSize: '0.74rem', fontWeight: '700', color: 'var(--goal-text-muted, #71817B)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Active Goal
              </span>
              <h4 style={{ fontSize: '1.2rem', fontWeight: '800', color: 'var(--goal-text-primary, #17231F)', margin: 0 }}>
                {goalLabel}
              </h4>
            </div>
          </div>
          <span style={{
            fontSize: '0.78rem',
            padding: '4px 10px',
            borderRadius: '8px',
            background: 'var(--goal-light-green, #E4F6EE)',
            color: 'var(--goal-primary, #16865F)',
            fontWeight: '700'
          }}>
            {progressPct}% Done
          </span>
        </div>

        {/* Progress Bar & Weight Trajectory */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.84rem', marginBottom: '8px' }}>
            <span style={{ color: 'var(--goal-text-secondary, #52635D)' }}>
              Current: <strong style={{ color: 'var(--goal-primary, #16865F)', fontWeight: '800' }}>{currentWt} kg</strong>
            </span>
            <span style={{ color: 'var(--goal-text-secondary, #52635D)' }}>
              Target: <strong style={{ color: 'var(--goal-blue, #2589D8)', fontWeight: '800' }}>{targetWt} kg</strong>
            </span>
          </div>

          <div style={{ height: '10px', background: '#E3EBE7', borderRadius: '9999px', overflow: 'hidden' }}>
            <div
              style={{
                height: '100%',
                width: `${Math.min(100, Math.max(4, progressPct))}%`,
                background: 'var(--goal-bright-green, #19B77A)',
                borderRadius: '9999px',
                transition: 'width 0.4s ease'
              }}
            />
          </div>
        </div>

        {/* Dynamic Metric Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          background: 'var(--goal-bg, #F7FAF8)',
          border: '1px solid var(--goal-border, #D5E2DC)',
          padding: '12px 14px',
          borderRadius: 'var(--radius-md)'
        }}>
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--goal-text-secondary, #52635D)', fontWeight: '600' }}>Weekly Target</div>
            <div style={{ fontSize: '0.94rem', fontWeight: '800', color: isAggressive ? 'var(--goal-danger, #DC5A5A)' : '#19A974', marginTop: '2px' }}>
              {weeklyPace} kg/wk
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--goal-text-secondary, #52635D)', fontWeight: '600' }}>Expected Date</div>
            <div style={{ fontSize: '0.94rem', fontWeight: '800', color: 'var(--goal-blue, #2589D8)', marginTop: '2px' }}>
              {estDate}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--goal-text-secondary, #52635D)', fontWeight: '600' }}>Remaining</div>
            <div style={{ fontSize: '0.94rem', fontWeight: '800', color: 'var(--goal-orange, #F28C28)', marginTop: '2px' }}>
              {remainingWt} kg
            </div>
          </div>
        </div>

        {/* Footer & Action */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem' }}>
          <span style={{ color: 'var(--goal-text-secondary, #52635D)' }}>
            Start: <strong style={{ color: 'var(--goal-text-primary, #17231F)' }}>{startWt} kg</strong> → Target: <strong style={{ color: 'var(--goal-blue, #2589D8)' }}>{targetWt} kg</strong>
          </span>
          <span style={{ color: 'var(--goal-primary, #16865F)', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '2px' }}>
            Update <ChevronRight size={14} />
          </span>
        </div>
      </div>

      {/* Goal Modal */}
      {showModal && (
        <GoalProgressModal
          isOpen={true}
          onClose={() => setShowModal(false)}
          progressData={progressData}
          onGoalUpdated={handleGoalOrWeightUpdated}
        />
      )}
    </>
  );
};

export default GoalProgressCard;
