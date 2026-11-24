"""Seed deterministic demo data by starting the API's idempotent seeder."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.main import init_db, seed

if __name__=='__main__':
    init_db(); seed(); print('Synthetic Chennai flood scenario is ready (seed=42).')
