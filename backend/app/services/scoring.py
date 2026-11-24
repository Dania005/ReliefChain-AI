from datetime import datetime, timezone
from ..config import URGENCY_WEIGHT

def priority_score(urgency:str,vulnerability_flags:list[str],waiting_minutes:float=0,hazard_risk:float=0,corroboration_count:int=1,duplicate:bool=False)->float:
    """Transparent 0–100 score; weights are intentionally simple for the synthetic demo."""
    urgency_term=URGENCY_WEIGHT.get(urgency,0)*45
    vulnerability=min(len(vulnerability_flags),4)*7
    waiting=min(max(waiting_minutes,0)/60,1)*15
    hazard=min(max(hazard_risk,0),1)*12
    corroboration=min(max(corroboration_count-1,0),5)*2
    penalty=18 if duplicate else 0
    return round(max(0,min(100,urgency_term+vulnerability+waiting+hazard+corroboration-penalty)),2)
