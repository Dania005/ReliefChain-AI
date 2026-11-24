from fastapi import HTTPException

TERMINAL = {"VERIFIED", "DUPLICATE", "CANCELLED"}
ALLOWED = {
    "RECEIVED": {"TRIAGED", "DUPLICATE", "CANCELLED", "ESCALATED"},
    "TRIAGED": {"MATCHED", "UNMATCHABLE", "CANCELLED", "ESCALATED"},
    "MATCHED": {"ACCEPTED", "REJECTED", "CANCELLED", "ESCALATED"},
    "ACCEPTED": {"DISPATCHED", "REJECTED", "CANCELLED", "ESCALATED"},
    "DISPATCHED": {"DELIVERED", "CANCELLED", "ESCALATED"},
    "DELIVERED": {"VERIFIED", "DISPUTED", "CANCELLED", "ESCALATED"},
    "DISPUTED": {"TRIAGED", "CANCELLED", "ESCALATED"},
    "UNMATCHABLE": {"ESCALATED", "TRIAGED", "CANCELLED"},
    "ESCALATED": {"TRIAGED", "MATCHED", "ACCEPTED", "DISPATCHED", "DELIVERED", "CANCELLED"},
    "REJECTED": {"TRIAGED", "CANCELLED"},
}

def validate_transition(source: str, target: str):
    if source == target or target not in ALLOWED.get(source, set()):
        raise HTTPException(409, detail={"error": "invalid_transition", "message": f"Cannot transition {source} to {target}"})

