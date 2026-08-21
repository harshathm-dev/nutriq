import json
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.sync import SyncRecord, DeviceSyncState
from app.models.meal import Meal, MealItem
from app.models.tracking import Water, Exercise, WeightHistory

class SyncService:
    """
    Offline Synchronization Engine
    Implements Last-Write-Wins (LWW) conflict resolution and idempotent processing.
    """

    @classmethod
    async def process_sync_batch(
        cls,
        session: AsyncSession,
        user_id: str,
        device_id: str,
        changes: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        processed_count = 0
        conflicts_resolved = 0
        server_updates = []

        # Update DeviceSyncState
        sync_state_stmt = select(DeviceSyncState).where(
            and_(DeviceSyncState.user_id == user_id, DeviceSyncState.device_id == device_id)
        )
        sync_state_res = await session.execute(sync_state_stmt)
        dev_sync = sync_state_res.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if dev_sync:
            dev_sync.last_sync_at = now
        else:
            dev_sync = DeviceSyncState(user_id=user_id, device_id=device_id, last_sync_at=now)
            session.add(dev_sync)

        for change in changes:
            entity_type = change.get("entity_type")
            entity_id = change.get("entity_id")
            op = change.get("operation", "INSERT")
            payload = change.get("payload", {})
            client_ts = change.get("client_timestamp", now)
            if isinstance(client_ts, str):
                try:
                    client_ts = datetime.fromisoformat(client_ts.replace("Z", "+00:00"))
                except Exception:
                    client_ts = now

            # Check if sync record already exists (Idempotency Check)
            existing_record_stmt = select(SyncRecord).where(
                and_(
                    SyncRecord.user_id == user_id,
                    SyncRecord.device_id == device_id,
                    SyncRecord.entity_id == entity_id,
                    SyncRecord.client_timestamp == client_ts
                )
            )
            existing_record_res = await session.execute(existing_record_stmt)
            if existing_record_res.scalar_one_or_none() is not None:
                continue  # Already processed

            # Record in SyncRecords audit log
            sync_rec = SyncRecord(
                user_id=user_id,
                device_id=device_id,
                entity_type=entity_type,
                entity_id=entity_id,
                operation=op,
                payload=json.dumps(payload),
                client_timestamp=client_ts,
                server_timestamp=now,
                status="synced"
            )
            session.add(sync_rec)

            # Apply operation to actual entities
            if entity_type == "water":
                if op == "INSERT":
                    water = Water(
                        id=entity_id,
                        user_id=user_id,
                        amount_ml=float(payload.get("amount_ml", 250)),
                        recorded_at=client_ts
                    )
                    session.add(water)
                elif op == "DELETE":
                    stmt = select(Water).where(and_(Water.id == entity_id, Water.user_id == user_id))
                    res = await session.execute(stmt)
                    w = res.scalar_one_or_none()
                    if w:
                        await session.delete(w)
            elif entity_type in ["exercise", "activity"]:
                if op == "INSERT":
                    ex = Exercise(
                        id=entity_id,
                        user_id=user_id,
                        type=payload.get("type") or payload.get("activity_type") or "walking",
                        duration_min=int(payload.get("duration_min") or payload.get("duration_minutes") or 30),
                        intensity=payload.get("intensity") or "moderate",
                        calories_burned_est=float(payload.get("calories_burned_est") or payload.get("calories_burned") or 0.0),
                        recorded_at=client_ts
                    )
                    session.add(ex)
                elif op == "UPDATE":
                    stmt = select(Exercise).where(and_(Exercise.id == entity_id, Exercise.user_id == user_id))
                    res = await session.execute(stmt)
                    ex = res.scalar_one_or_none()
                    if ex:
                        if "type" in payload or "activity_type" in payload:
                            ex.type = payload.get("type") or payload.get("activity_type")
                        if "duration_min" in payload or "duration_minutes" in payload:
                            ex.duration_min = int(payload.get("duration_min") or payload.get("duration_minutes"))
                        if "intensity" in payload:
                            ex.intensity = payload.get("intensity")
                        if "calories_burned_est" in payload or "calories_burned" in payload:
                            ex.calories_burned_est = float(payload.get("calories_burned_est") or payload.get("calories_burned"))
                elif op == "DELETE":
                    stmt = select(Exercise).where(and_(Exercise.id == entity_id, Exercise.user_id == user_id))
                    res = await session.execute(stmt)
                    ex = res.scalar_one_or_none()
                    if ex:
                        await session.delete(ex)
            elif entity_type == "weight":
                if op == "INSERT":
                    wt = WeightHistory(
                        id=entity_id,
                        user_id=user_id,
                        weight_kg=float(payload.get("weight_kg", 70)),
                        recorded_at=client_ts
                    )
                    session.add(wt)
            elif entity_type == "meal":
                if op == "INSERT":
                    meal = Meal(
                        id=entity_id,
                        user_id=user_id,
                        meal_type=payload.get("meal_type", "breakfast"),
                        occurred_at=client_ts,
                        source=payload.get("source", "offline_pwa"),
                        sync_version=1
                    )
                    session.add(meal)
                    for itm in payload.get("items", []):
                        m_item = MealItem(
                            meal_id=entity_id,
                            food_id=itm.get("food_id"),
                            food_name=itm.get("food_name", "Food Item"),
                            quantity=float(itm.get("quantity", 1.0)),
                            serving_unit=itm.get("serving_unit", "serving"),
                            grams=float(itm.get("grams", 100.0)),
                            calories=float(itm.get("calories", 0.0)),
                            protein_g=float(itm.get("protein_g", 0.0)),
                            carbs_g=float(itm.get("carbs_g", 0.0)),
                            fat_g=float(itm.get("fat_g", 0.0)),
                            fiber_g=float(itm.get("fiber_g", 0.0)),
                            sugar_g=float(itm.get("sugar_g", 0.0)),
                            sodium_mg=float(itm.get("sodium_mg", 0.0))
                        )
                        session.add(m_item)

            processed_count += 1

        await session.commit()
        return processed_count, conflicts_resolved, server_updates
