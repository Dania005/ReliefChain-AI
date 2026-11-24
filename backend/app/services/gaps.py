from ..db import connect
from datetime import datetime,timezone

def detect_gaps():
    gaps=[]
    with connect() as c:
        rows=c.execute("SELECT q.*,m.state match_state FROM requests q LEFT JOIN matches m ON m.request_id=q.id AND m.state IN ('PROPOSED','ACCEPTED','DISPATCHED') WHERE q.status NOT IN ('VERIFIED','DUPLICATE','CANCELLED')").fetchall()
        for r in rows:
            typ=None; action='Review and assign an owner'
            if not r['owner_id']: typ='NO_OWNER'
            if r['status']=='TRIAGED' and not r['match_state']: typ='NO_RESOURCE_IN_RANGE'; action='Source the missing resource or increase the search radius'
            if r['status']=='MATCHED' and r['match_state']=='PROPOSED': typ='MATCHED_NOT_ACCEPTED'; action='Contact agency coordinator; reassign if unacknowledged'
            if r['status']=='DELIVERED': typ='DELIVERED_UNVERIFIED'; action='Request confirmation or create a volunteer spot-check'
            if typ: gaps.append({"request_id":r['id'],"gap_type":typ,"severity":r['urgency'],"responsible_party":r['owner_id'] or 'District control room',"recommended_action":action})
        unmet=c.execute("SELECT ward_id,need_type,SUM(COALESCE(quantity,1)) quantity FROM requests WHERE status NOT IN ('VERIFIED','DUPLICATE','CANCELLED') AND duplicate_of IS NULL GROUP BY ward_id,need_type").fetchall()
    return {"gaps":gaps,"unmet_need":[dict(x) for x in unmet]}
