import React, { useState, useEffect, useRef } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import {
  Calendar, ChevronLeft, ChevronRight, Activity, Flame, Clock,
  Footprints, Navigation, Plus, Trash2, Edit2, CheckCircle2,
  AlertCircle, RefreshCw, Dumbbell
} from 'lucide-react';
import {
  getToday,
  addDays,
  subtractDays,
  formatDate,
  isToday as checkIsToday,
  isFuture as checkIsFuture,
  formatTime
} from '../utils/dateUtils';
import { ActivityModal } from '../components/ActivityModal';

export const ActivityHistoryPage = () => {
  const { navigate, refreshAllData } = useStore();

  const getInitialDate = () => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const qDate = params.get('date');
      if (qDate && /^\d{4}-\d{2}-\d{2}$/.test(qDate)) {
        return qDate;
      }
    }
    return getToday();
  };

  const [selectedDate, setSelectedDate] = useState(getInitialDate());
  const [historyData, setHistoryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editingActivity, setEditingActivity] = useState(null);

  const activeRequestIdRef = useRef(0);

  const isSelectedToday = checkIsToday(selectedDate);
  const isSelectedFuture = checkIsFuture(selectedDate);

  useEffect(() => {
    fetchHistory(selectedDate);
  }, [selectedDate]);

  const fetchHistory = async (dateStr) => {
    const reqId = ++activeRequestIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getActivityHistory(dateStr);
      if (reqId === activeRequestIdRef.current) {
        setHistoryData(data);
      }
    } catch (err) {
      console.warn("Failed to fetch activity history:", err);
      if (reqId === activeRequestIdRef.current) {
        setError("Unable to load activity history for this date.");
      }
    } finally {
      if (reqId === activeRequestIdRef.current) {
        setLoading(false);
      }
    }
  };

  const handlePrevDay = () => {
    setSelectedDate(prev => subtractDays(prev, 1));
  };

  const handleNextDay = () => {
    setSelectedDate(prev => addDays(prev, 1));
  };

  const handleToday = () => {
    setSelectedDate(getToday());
  };

  const handleDeleteActivity = async (activityId) => {
    if (!window.confirm("Are you sure you want to delete this activity record?")) {
      return;
    }
    try {
      await api.deleteActivity(activityId);
      await fetchHistory(selectedDate);
      await refreshAllData();
    } catch (err) {
      console.error("Failed to delete activity:", err);
      alert("Unable to delete activity. Please try again.");
    }
  };

  const handleEditActivity = (act) => {
    setEditingActivity(act);
    setShowModal(true);
  };

  const handleAddActivity = () => {
    setEditingActivity(null);
    setShowModal(true);
  };

  const totalCalories = Math.round(historyData?.total_calories_burned || 0);
  const totalDuration = historyData?.total_duration_minutes || 0;
  const totalSteps = historyData?.total_steps || 0;
  const activities = historyData?.activities || [];

  return (
    <div className="page-container">
      
      {/* 1. Header & Date Navigation Bar */}
      <div className="wellness-card" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)', marginBottom: '4px' }}>
              <Activity size={22} />
              <h1 style={{ fontSize: '1.5rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
                Physical Activity History
              </h1>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', margin: 0 }}>
              Chronological log of workouts, daily calories burned, and step counts.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            {/* Strict 1-Calendar Day Navigation Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--bg-subtle)', padding: '4px 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-glass)' }}>
              <button
                type="button"
                onClick={handlePrevDay}
                className="btn-secondary"
                style={{ padding: '6px 10px', fontSize: '0.8rem', gap: '4px' }}
                title="Previous Day (1 day back)"
              >
                <ChevronLeft size={16} /> Prev
              </button>

              <input
                type="date"
                value={selectedDate}
                onChange={(e) => {
                  if (e.target.value) setSelectedDate(e.target.value);
                }}
                className="input-field"
                style={{ height: '34px', fontSize: '0.84rem', padding: '4px 8px', width: '135px' }}
              />

              <button
                type="button"
                onClick={handleToday}
                className={isSelectedToday ? "btn-primary" : "btn-secondary"}
                style={{ padding: '6px 12px', fontSize: '0.8rem' }}
              >
                Today
              </button>

              <button
                type="button"
                onClick={handleNextDay}
                className="btn-secondary"
                style={{ padding: '6px 10px', fontSize: '0.8rem', gap: '4px' }}
                title="Next Day (1 day forward)"
              >
                Next <ChevronRight size={16} />
              </button>
            </div>

            <button
              type="button"
              onClick={handleAddActivity}
              className="btn-primary"
              style={{ padding: '8px 16px', fontSize: '0.84rem' }}
            >
              <Plus size={16} /> Log Activity
            </button>
          </div>
        </div>
      </div>

      {/* 2. Top Summary Metrics Card */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <div className="wellness-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '6px', background: 'var(--primary-light)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Flame size={16} />
            </div>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>
              Calories Burned
            </span>
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: '800', color: 'var(--primary)' }}>
            {totalCalories} <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>kcal</span>
          </div>
          <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
            MET calibrated energy
          </span>
        </div>

        <div className="wellness-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '6px', background: 'var(--calorie-orange-light)', color: 'var(--calorie-orange)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Clock size={16} />
            </div>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>
              Active Duration
            </span>
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: '800', color: 'var(--calorie-orange)' }}>
            {totalDuration} <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>min</span>
          </div>
          <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
            Total workout time
          </span>
        </div>

        <div className="wellness-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '6px', background: 'var(--macro-protein-light)', color: 'var(--macro-protein)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Footprints size={16} />
            </div>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>
              Step Count
            </span>
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: '800', color: 'var(--macro-protein)' }}>
            {totalSteps.toLocaleString()} <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>steps</span>
          </div>
          <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
            Recorded steps
          </span>
        </div>

        <div className="wellness-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '6px', background: 'var(--hydration-cyan-light)', color: 'var(--hydration-cyan)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Activity size={16} />
            </div>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', fontWeight: '700', textTransform: 'uppercase' }}>
              Activities Recorded
            </span>
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: '800', color: 'var(--hydration-cyan)' }}>
            {activities.length} <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>sessions</span>
          </div>
          <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
            For {formatDate(selectedDate, 'month_day')}
          </span>
        </div>
      </div>

      {/* 3. Loading, Error, and Activity Cards */}
      {loading ? (
        <div className="wellness-card" style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 12px auto', color: 'var(--primary)' }} />
          <p style={{ margin: 0, fontSize: '0.9rem' }}>Loading activity records for {formatDate(selectedDate)}...</p>
        </div>
      ) : error ? (
        <div className="wellness-card" style={{ padding: '36px 24px', textAlign: 'center', border: '1px solid rgba(217, 93, 93, 0.3)', background: 'var(--error-bg)' }}>
          <AlertCircle size={28} color="var(--error-rose)" style={{ margin: '0 auto 10px auto' }} />
          <p style={{ color: 'var(--error-rose)', fontWeight: '700', marginBottom: '14px' }}>{error}</p>
          <button
            type="button"
            onClick={() => fetchHistory(selectedDate)}
            className="btn-primary"
            style={{ padding: '8px 18px', fontSize: '0.84rem' }}
          >
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      ) : activities.length === 0 ? (
        <div className="wellness-card" style={{ padding: '56px 24px', textAlign: 'center' }}>
          <div style={{ width: '56px', height: '56px', borderRadius: '50%', background: 'var(--bg-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px auto', color: 'var(--text-muted)' }}>
            <Dumbbell size={28} />
          </div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: '800', margin: '0 0 6px 0', color: 'var(--text-primary)' }}>
            No physical activity recorded for this date.
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: '420px', margin: '0 auto 20px auto' }}>
            No workouts or active sessions were logged for {formatDate(selectedDate)}.
          </p>
          <button
            type="button"
            onClick={handleAddActivity}
            className="btn-primary"
            style={{ padding: '10px 22px', fontSize: '0.88rem' }}
          >
            <Plus size={16} /> Log Activity for {formatDate(selectedDate, 'month_day')}
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {activities.map((act) => {
            const timeStr = act.time || formatTime(act.recorded_at);
            const friendlyName = act.activity_name || act.activity_type || act.type || 'Workout';
            const calBurned = Math.round(act.calories_burned || act.calories_burned_est || 0);

            return (
              <div
                key={act.id}
                className="wellness-card"
                style={{
                  padding: '20px 24px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '16px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{
                    width: '46px',
                    height: '46px',
                    borderRadius: '12px',
                    background: 'var(--primary-light)',
                    color: 'var(--primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: 'var(--shadow-sm)'
                  }}>
                    <Activity size={22} />
                  </div>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                        {friendlyName}
                      </h3>
                      {timeStr && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '3px' }}>
                          <Clock size={12} /> {timeStr}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      <span>Duration: <strong>{act.duration_minutes || act.duration_min} min</strong></span>
                      <span>•</span>
                      <span>Intensity: <strong style={{ textTransform: 'capitalize' }}>{act.intensity || 'moderate'}</strong></span>
                      {act.steps > 0 && (
                        <>
                          <span>•</span>
                          <span>Steps: <strong>{act.steps.toLocaleString()}</strong></span>
                        </>
                      )}
                      {act.distance_km > 0 && (
                        <>
                          <span>•</span>
                          <span>Distance: <strong>{act.distance_km} km</strong></span>
                        </>
                      )}
                    </div>

                    {act.notes && (
                      <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '6px 0 0 0', fontStyle: 'italic' }}>
                        "{act.notes}"
                      </p>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.35rem', fontWeight: '800', color: 'var(--primary)' }}>
                      -{calBurned} <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>kcal</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <button
                      type="button"
                      onClick={() => handleEditActivity(act)}
                      className="btn-secondary"
                      style={{ padding: '7px 10px', fontSize: '0.78rem', gap: '4px' }}
                    >
                      <Edit2 size={13} /> Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteActivity(act.id)}
                      className="btn-secondary"
                      style={{ padding: '7px 10px', fontSize: '0.78rem', color: 'var(--error-rose)', borderColor: 'rgba(217, 93, 93, 0.3)' }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <ActivityModal
          isOpen={showModal}
          onClose={() => { setShowModal(false); setEditingActivity(null); }}
          onActivityLogged={() => { fetchHistory(selectedDate); refreshAllData(); }}
          defaultDate={selectedDate}
          editingActivity={editingActivity}
        />
      )}

    </div>
  );
};
