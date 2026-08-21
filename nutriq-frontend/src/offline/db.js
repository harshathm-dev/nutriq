import Dexie from 'dexie';

export const db = new Dexie('NutriQOfflineDB');

db.version(2).stores({
  profile: 'id, user_id, name',
  foods: 'id, name, category, barcode',
  meals: 'id, meal_type, occurred_at, sync_status, date',
  water_logs: 'id, recorded_at, sync_status, date',
  exercise_logs: 'id, recorded_at, sync_status, date',
  weight_logs: 'id, recorded_at, sync_status, date',
  daily_summaries: 'date, updated_at',
  weekly_summaries: 'week_start, updated_at',
  sync_queue: '++id, entity_type, entity_id, operation, client_timestamp',
  reminder_settings: 'id, updated_at'
});

export const ensureDbOpen = async () => {
  try {
    if (!db.isOpen()) {
      await db.open();
    }
  } catch (err) {
    console.warn("Could not ensure IndexedDB is open:", err);
  }
};

export const clearUserLocalData = async () => {
  try {
    await ensureDbOpen();
    if (db.isOpen()) {
      await Promise.all([
        db.meals.clear().catch(() => {}),
        db.water_logs.clear().catch(() => {}),
        db.exercise_logs.clear().catch(() => {}),
        db.weight_logs.clear().catch(() => {}),
        db.daily_summaries.clear().catch(() => {}),
        db.weekly_summaries.clear().catch(() => {}),
        db.profile.clear().catch(() => {}),
        db.reminder_settings.clear().catch(() => {}),
        db.sync_queue.clear().catch(() => {})
      ]);
    }
  } catch (err) {
    console.warn("Could not clear user local data:", err);
  }
};

export const enqueueOfflineAction = async (entityType, entityId, operation, payload) => {
  try {
    await ensureDbOpen();
    if (db.isOpen()) {
      await db.sync_queue.add({
        entity_type: entityType,
        entity_id: entityId,
        operation: operation,
        payload: payload,
        client_timestamp: new Date().toISOString()
      });
    }
  } catch (err) {
    console.error("Failed to enqueue offline action:", err);
  }
};



