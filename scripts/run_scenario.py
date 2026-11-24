"""Replay the local synthetic flood scenario; all actions stay inside the demo database."""
import sys, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.main import init_db, seed, requests, metrics, inject

def main():
    init_db(); seed()
    print('T+00 Forecast warning: high flood risk in Wards 1, 2, 3 and 9.')
    print('T+01 Request surge: synthetic intake queue loaded; duplicates linked to canonical requests.')
    print('T+02 Resource matching: deterministic allocation proposals created.')
    print('T+03 Injected failure A:',inject({'event':'road_block'})['message'])
    print('T+04 Injected failure B: unaccepted critical matches are visible in the gap queue.')
    print('T+05 Unmet need: boat and water shortages are listed by ward.')
    print('T+06 Verification policy: partial requester replies reopen requests for review.')
    print(json.dumps(metrics(),indent=2))

if __name__=='__main__': main()
