import math, uuid
from datetime import datetime, timezone
from ..db import connect, now

def distance_km(a_lat,a_lng,b_lat,b_lng):
    if None in (a_lat,a_lng,b_lat,b_lng): return 9999
    return 6371*2*math.asin(math.sqrt(math.sin(math.radians(b_lat-a_lat)/2)**2+math.cos(math.radians(a_lat))*math.cos(math.radians(b_lat))*math.sin(math.radians(b_lng-a_lng)/2)**2))

def allocate(request_id: str) -> list[dict]:
    """OR-Tools assignment when installed; deterministic greedy fallback."""
    with connect() as c:
        q=c.execute("SELECT * FROM requests WHERE id=?",(request_id,)).fetchone()
        if not q: return []
        # Drop this request's stale proposal set before rematching. Other proposed
        # allocations reserve stock logically until accepted or rejected.
        c.execute("DELETE FROM matches WHERE request_id=? AND state='PROPOSED'",(request_id,))
        resources=c.execute("SELECT r.*,a.name agency_name,a.ward_coverage,COALESCE((SELECT SUM(m.quantity_allocated) FROM matches m WHERE m.resource_id=r.id AND m.state='PROPOSED' AND m.request_id<>?),0) reserved FROM resources r LEFT JOIN agencies a ON a.id=r.agency_id WHERE r.type=? AND r.quantity_available>0 AND r.status!='STALE'",(request_id,q['need_type'])).fetchall()
        roads=c.execute("SELECT * FROM roads WHERE flooded=1").fetchall()
    road_block=bool(roads)
    choices=[]
    for r in resources:
        if road_block and r['mobility']=='vehicle': continue
        d=distance_km(q['lat'],q['lng'],r['lat'],r['lng'])
        if d>35: continue
        effective_available=max(0,float(r['quantity_available'])-float(r['reserved'] or 0))
        qty=min(float(q['quantity'] or 1),effective_available)
        if qty<=0: continue
        eta=max(5,int(d*4+8))
        score=(q['priority_score'] or 0)*100-d*2+(5 if q['ward_id'] in (r['ward_coverage'] or '') else 0)
        choices.append((score,d,r,qty,eta))
    choices.sort(key=lambda x:(-x[0],x[1]))
    # CP-SAT optional; using it for single-request capacity selection is exact and tiny.
    selected=[]
    try:
        from ortools.sat.python import cp_model
        model=cp_model.CpModel(); take=[model.NewBoolVar(f"r{i}") for i in range(len(choices))]
        # maximize fulfilled units, with distance/priority tie breaking.
        demand=int(q['quantity'] or 1)
        model.Add(sum(int(ch[3])*take[i] for i,ch in enumerate(choices))<=demand)
        model.Maximize(sum((10000+max(-1000,min(1000,int(ch[0]))))*int(ch[3])*take[i]-100*take[i] for i,ch in enumerate(choices)))
        solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=1
        if solver.Solve(model) in (cp_model.OPTIMAL,cp_model.FEASIBLE): selected=[ch for i,ch in enumerate(choices) if solver.Value(take[i])]
    except ImportError:
        remaining=float(q['quantity'] or 1)
        for ch in choices:
            if remaining<=0: break
            qty=min(ch[3],remaining); selected.append((*ch[:3],qty,ch[4])); remaining-=qty
    # Cap each proposal to remaining demand even if a solver returns a subset
    # whose whole-resource quantities exceed the remaining request amount.
    remaining=float(q['quantity'] or 1); bounded=[]
    for ch in selected:
        qty=min(ch[3],remaining)
        if qty>0: bounded.append((*ch[:3],qty,ch[4])); remaining-=qty
    selected=bounded
    result=[]
    with connect() as c:
        for score,d,r,qty,eta in selected:
            mid=str(uuid.uuid4()); expl=f"{r['agency_name'] or 'Agency'} selected: {d:.1f} km away, {qty:g} {q['unit'] or 'units'} available; ETA {eta} min."
            c.execute("INSERT INTO matches VALUES(?,?,?,?,?,?,?,?,?,?,?)",(mid,request_id,r['id'],qty,eta,None,score,'PROPOSED',expl,now(),None))
            result.append({"id":mid,"resource_id":r['id'],"quantity_allocated":qty,"eta_minutes":eta,"score":score,"state":"PROPOSED","explanation":expl})
    return result
