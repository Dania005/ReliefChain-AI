"""Small SQLite persistence layer. SQLite keeps the demo self-contained and offline."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .config import DB_PATH

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS agencies(id TEXT PRIMARY KEY,name TEXT,type TEXT,contact TEXT,ward_coverage TEXT,authority_level INTEGER,parent_agency_id TEXT);
        CREATE TABLE IF NOT EXISTS resources(id TEXT PRIMARY KEY,agency_id TEXT,type TEXT,quantity_total INTEGER,quantity_available INTEGER,unit TEXT,lat REAL,lng REAL,vehicle_capacity INTEGER,mobility TEXT,status TEXT,last_updated_at TEXT);
        CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,source_channel TEXT,raw_text TEXT,language TEXT,translated_text TEXT,need_type TEXT,quantity REAL,unit TEXT,lat REAL,lng REAL,ward_id TEXT,address_text TEXT,location_confidence REAL,urgency TEXT,vulnerability_flags TEXT,priority_score REAL,status TEXT,duplicate_of TEXT,corroboration_count INTEGER DEFAULT 1,trust_score REAL,verified_requester INTEGER,owner_type TEXT,owner_id TEXT,sla_due_at TEXT,last_progress_at TEXT,escalation_level INTEGER DEFAULT 0,created_at TEXT,updated_at TEXT);
        CREATE TABLE IF NOT EXISTS matches(id TEXT PRIMARY KEY,request_id TEXT,resource_id TEXT,quantity_allocated REAL,eta_minutes INTEGER,route_polyline TEXT,score REAL,state TEXT,explanation TEXT,proposed_at TEXT,accepted_at TEXT);
        CREATE TABLE IF NOT EXISTS status_events(id TEXT PRIMARY KEY,request_id TEXT,from_status TEXT,to_status TEXT,actor_type TEXT,actor_id TEXT,reason TEXT,payload TEXT,timestamp TEXT);
        CREATE TABLE IF NOT EXISTS escalations(id TEXT PRIMARY KEY,request_id TEXT,level INTEGER,reason_code TEXT,notified_party_id TEXT,channel TEXT,message TEXT,acknowledged_at TEXT,timestamp TEXT);
        CREATE TABLE IF NOT EXISTS verifications(id TEXT PRIMARY KEY,request_id TEXT,method TEXT,result TEXT,evidence_url TEXT,timestamp TEXT);
        CREATE TABLE IF NOT EXISTS agent_traces(id TEXT PRIMARY KEY,request_id TEXT,agent TEXT,action TEXT,tool TEXT,outcome TEXT,details TEXT,timestamp TEXT);
        CREATE TABLE IF NOT EXISTS roads(id TEXT PRIMARY KEY,from_node TEXT,to_node TEXT,length_m REAL,flooded INTEGER,passable_for TEXT,updated_at TEXT);
        CREATE TABLE IF NOT EXISTS forecasts(ward_id TEXT,hazard TEXT,risk REAL,horizon_hours INTEGER,predicted_demand TEXT,generated_at TEXT,PRIMARY KEY(ward_id,hazard,horizon_hours));
        """)

def trace(request_id: str, agent: str, action: str, tool: str, outcome: str, details: dict):
    import uuid
    with connect() as c:
        c.execute("INSERT INTO agent_traces VALUES(?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), request_id, agent, action, tool, outcome, json.dumps(details), now()))

