"""SQLModel table definitions for Postgres-compatible migration paths.

The offline demo runtime uses db.py's SQLite adapter to avoid requiring a database server.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid

def uid(): return str(uuid.uuid4())
def utcnow(): return datetime.now(timezone.utc)

class Request(SQLModel, table=True):
    id: str = Field(default_factory=uid, primary_key=True); source_channel: str; raw_text: str; language: str='other'; translated_text: str=''
    need_type: str='OTHER'; quantity: Optional[float]=None; unit: Optional[str]=None; lat: Optional[float]=None; lng: Optional[float]=None; ward_id: Optional[str]=None; address_text: Optional[str]=None
    location_confidence: float=.1; urgency: str='MEDIUM'; vulnerability_flags: str='[]'; priority_score: float=0; status: str='RECEIVED'; duplicate_of: Optional[str]=None; trust_score: float=.5; verified_requester: bool=False
    owner_type: Optional[str]=None; owner_id: Optional[str]=None; sla_due_at: Optional[datetime]=None; last_progress_at: Optional[datetime]=None; escalation_level: int=0; created_at: datetime=Field(default_factory=utcnow); updated_at: datetime=Field(default_factory=utcnow)

class Agency(SQLModel, table=True):
    id: str=Field(default_factory=uid,primary_key=True); name: str; type: str; contact: str=''; ward_coverage: str='[]'; authority_level: int=0; parent_agency_id: Optional[str]=None; created_at: datetime=Field(default_factory=utcnow); updated_at: datetime=Field(default_factory=utcnow)

class Resource(SQLModel, table=True):
    id: str=Field(default_factory=uid,primary_key=True); agency_id: str; type: str; quantity_total: int; quantity_available: int; unit: str; lat: float; lng: float; vehicle_capacity: Optional[int]=None; mobility: str='static'; status: str='AVAILABLE'; last_updated_at: datetime=Field(default_factory=utcnow); created_at: datetime=Field(default_factory=utcnow); updated_at: datetime=Field(default_factory=utcnow)

class StatusEvent(SQLModel, table=True):
    id: str=Field(default_factory=uid,primary_key=True); request_id: str; from_status: str; to_status: str; actor_type: str; actor_id: str; reason: str=''; payload: str='{}'; timestamp: datetime=Field(default_factory=utcnow)

