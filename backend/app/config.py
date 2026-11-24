from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("DATABASE_URL", str(ROOT / "reliefchain.db")).replace("sqlite:///", ""))
SIM_SPEED = float(os.getenv("SIM_SPEED", "1"))
APP_NAME = "ReliefChain AI"
SLA_MINUTES = {
    "CRITICAL": {"TRIAGE": 2, "MATCH": 5, "ACCEPT": 5, "DISPATCH": 10, "DELIVER": 45, "VERIFY": 30},
    "HIGH": {"TRIAGE": 5, "MATCH": 15, "ACCEPT": 15, "DISPATCH": 30, "DELIVER": 120, "VERIFY": 60},
    "MEDIUM": {"TRIAGE": 15, "MATCH": 45, "ACCEPT": 30, "DISPATCH": 90, "DELIVER": 360, "VERIFY": 180},
    "LOW": {"TRIAGE": 60, "MATCH": 180, "ACCEPT": 120, "DISPATCH": 240, "DELIVER": 720, "VERIFY": 480},
}
URGENCY_WEIGHT = {"CRITICAL": 1.0, "HIGH": .75, "MEDIUM": .5, "LOW": .25}

