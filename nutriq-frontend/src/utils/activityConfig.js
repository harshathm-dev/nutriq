/**
 * Centralized Physical Activity MET Configuration for NutriQ
 * 
 * Formula:
 * Calories burned = MET * 3.5 * weight_kg / 200 * duration_minutes
 */

export const ACTIVITY_TYPES = [
  { id: 'walking', label: 'Walking', icon: '🚶', defaultDuration: 30, mets: { low: 2.8, moderate: 3.5, high: 4.5 } },
  { id: 'running', label: 'Running', icon: '🏃', defaultDuration: 30, mets: { low: 7.0, moderate: 9.8, high: 12.0 } },
  { id: 'jogging', label: 'Jogging', icon: '🏃‍♂️', defaultDuration: 30, mets: { low: 6.0, moderate: 7.5, high: 9.0 } },
  { id: 'cycling', label: 'Cycling', icon: '🚴', defaultDuration: 30, mets: { low: 5.5, moderate: 7.5, high: 10.0 } },
  { id: 'swimming', label: 'Swimming', icon: '🏊', defaultDuration: 30, mets: { low: 5.0, moderate: 7.0, high: 9.5 } },
  { id: 'gym_workout', label: 'Gym / Strength Training', icon: '🏋️', defaultDuration: 45, mets: { low: 4.0, moderate: 6.0, high: 8.0 } },
  { id: 'weight_training', label: 'Weight Training', icon: '💪', defaultDuration: 45, mets: { low: 3.8, moderate: 5.5, high: 7.5 } },
  { id: 'yoga', label: 'Yoga', icon: '🧘', defaultDuration: 30, mets: { low: 2.5, moderate: 3.2, high: 4.0 } },
  { id: 'sports', label: 'Sports', icon: '⚽', defaultDuration: 45, mets: { low: 5.0, moderate: 7.0, high: 9.0 } },
  { id: 'household', label: 'Household Activity', icon: '🧹', defaultDuration: 30, mets: { low: 2.0, moderate: 3.0, high: 4.0 } },
  { id: 'other', label: 'Other', icon: '⚡', defaultDuration: 30, mets: { low: 3.0, moderate: 4.5, high: 6.0 } }
];

export const INTENSITY_LEVELS = [
  { id: 'low', label: 'Light', description: 'Light breathing, casual pace' },
  { id: 'moderate', label: 'Moderate', description: 'Elevated heart rate, comfortable breathing' },
  { id: 'high', label: 'Vigorous', description: 'Heavy breathing, high cardiovascular exertion' }
];

export const calculateCaloriesBurned = (activityTypeId, durationMinutes, intensity = 'moderate', weightKg = 70.0) => {
  const duration = Math.max(0, parseFloat(durationMinutes) || 0);
  if (duration === 0) return 0;

  const activity = ACTIVITY_TYPES.find(a => a.id === activityTypeId) || ACTIVITY_TYPES.find(a => a.id === 'other');
  // Normalize intensity
  let intKey = (intensity || 'moderate').toLowerCase();
  if (intKey === 'light') intKey = 'low';
  if (intKey === 'vigorous') intKey = 'high';

  const met = activity?.mets?.[intKey] || activity?.mets?.moderate || 4.5;
  const weight = Math.max(30, parseFloat(weightKg) || 70.0);

  // Standard MET formula: MET * 3.5 * weight_kg / 200 * duration_minutes
  const burned = (met * 3.5 * weight / 200.0) * duration;
  return Math.round(burned * 10) / 10;
};
