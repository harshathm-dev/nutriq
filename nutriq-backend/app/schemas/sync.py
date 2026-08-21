from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel

class SyncRecordSchema(BaseModel):
    id: Optional[str] = None
    device_id: Optional[str] = None
    entity_type: str  # "meal", "water", "exercise", "weight"
    entity_id: str
    operation: str  # "INSERT", "UPDATE", "DELETE"
    payload: Dict[str, Any]
    client_timestamp: Optional[datetime] = None

class SyncBatchRequest(BaseModel):
    device_id: str
    last_sync_at: Optional[datetime] = None
    changes: List[SyncRecordSchema] = []

class SyncBatchResponse(BaseModel):
    status: str = "success"
    processed_count: int
    conflicts_resolved: int
    server_sync_timestamp: datetime
    server_updates: List[Dict[str, Any]] = []
