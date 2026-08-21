# NutriQ Offline-First Architecture & Synchronization

## Offline-First Philosophy
NutriQ ensures core food logging, calorie calculation, and progress tracking remain fully functional without internet connectivity.

## Client Storage (Dexie.js IndexedDB)
- `profile`: Local cache of user demographics and target formulas.
- `foods`: Cached catalog of verified Indian & international foods.
- `meals`: Locally stored meals and active logs.
- `water_logs`, `exercise_logs`, `weight_logs`: Local tracking records.
- `sync_queue`: Outbox queue of pending operations (`INSERT`, `UPDATE`, `DELETE`) with client timestamps.

## Synchronization Protocol
1. **Local Action**: User logs a meal or water offline → UI updates immediately via optimistic local transaction → `SyncRecord` is enqueued in `sync_queue`.
2. **Connectivity Detection**: `window.addEventListener('online')` triggers background `flushSyncQueue()`.
3. **Idempotency Check**: Server checks `device_id`, `entity_id`, and `client_timestamp` against `sync_records` table to prevent duplicates.
4. **Conflict Resolution Strategy**:
   - **Last-Write-Wins (LWW) by timestamp** at the record level.
   - **Field-level merge** for non-conflicting fields.
   - For conflicting meal edits on separate devices, the later timestamp persists while the earlier record is preserved in the change log.
5. **Queue Cleanup**: Local queue is cleared upon server acknowledgement.
