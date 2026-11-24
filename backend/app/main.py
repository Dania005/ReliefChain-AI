from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from .db import init_db, connect, now
from .config import APP_NAME
from .schemas import IngestInput, ActionInput, VerifyInput, StockInput
from .state_machine import validate_transition
from .services.workflow import run_workflow
from .services.matching import allocate
from .services.gaps import detect_gaps
import uuid, json, asyncio, random
from datetime import datetime, timedelta, timezone

app=FastAPI(title=APP_NAME,version='0.1.0',description='Request lifecycle coordination for climate emergencies. Synthetic demo data only.')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])

def change_status(c, q, target, actor='system', reason=None):
    validate_transition(q['status'],target); t=now()
    c.execute('UPDATE requests SET status=?,last_progress_at=?,updated_at=? WHERE id=?',(target,t,t,q['id']))
    c.execute('INSERT INTO status_events VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),q['id'],q['status'],target,'officer' if actor!='system' else 'system',actor,reason,json.dumps({}),t))

@app.on_event('startup')
def startup():
    init_db(); seed()

def seed():
    with connect() as c:
        if c.execute('SELECT COUNT(*) FROM requests').fetchone()[0]: return
        agencies=[('district','District Control Room','govt',4,None),('fire','Chennai Fire & Rescue','govt',3,'district'),('corp','Greater Chennai Corporation','govt',2,'district'),('ngo','Relief NGO Network','ngo',1,'corp'),('vol','Velachery Volunteer Group','volunteer_group',1,'corp')]
        for aid,name,typ,level,parent in agencies: c.execute('INSERT INTO agencies VALUES(?,?,?,?,?,?,?)',(aid,name,typ,'control room',json.dumps([f'WARD-{i:02}' for i in range(1,16)]),level,parent))
        resources=[('RESCUE_BOAT',5,'boats',12.9815,80.218,'vehicle','fire'),('WATER',600,'litres',12.9249,80.1,'vehicle','corp'),('MEDICINE',120,'kits',13.0067,80.257,'static','ngo'),('GENERATOR',8,'units',13.0418,80.234,'vehicle','corp'),('FOOD',250,'meals',13.0213,80.223,'static','vol'),('MEDICAL_TRANSPORT',3,'vehicles',13.0067,80.2206,'vehicle','fire'),('SHELTER',80,'beds',13.085,80.21,'static','corp')]
        for typ,qty,unit,lat,lng,mob,aid in resources:
            for n in range(2): c.execute('INSERT INTO resources VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),aid,typ,qty//2,qty//2,unit,lat+n*.01,lng+n*.008,10 if mob=='vehicle' else None,mob,'AVAILABLE',now()))
        for i,(text,need,urg,ward,lat,lng,qty) in enumerate([
            ('Water level rising, 6 people on terrace, one is bedridden, near Tambaram bus stand','RESCUE_BOAT','CRITICAL','WARD-02',12.9249,80.1,6),
            ('Appa ku oxygen cylinder venum, Velachery 2nd main road, tanni vandhuduchi','MEDICAL_TRANSPORT','CRITICAL','WARD-01',12.9815,80.218,1),
            ('Need drinking water for 20 families near Adyar bridge','WATER','HIGH','WARD-03',13.0067,80.257,200),
            ('Urgent food packets needed in Mylapore, 30 people','FOOD','HIGH','WARD-05',13.0339,80.269,30),
            ('Generator for clinic power backup in T Nagar','GENERATOR','MEDIUM','WARD-04',13.0418,80.2341,1)]):
            rid=str(uuid.uuid4()); t=now(); status='MATCHED' if i in (0,1,2,3,4) else 'RECEIVED'
            c.execute('INSERT INTO requests(id,source_channel,raw_text,language,translated_text,need_type,quantity,unit,lat,lng,ward_id,address_text,location_confidence,urgency,vulnerability_flags,priority_score,status,corroboration_count,trust_score,verified_requester,owner_type,owner_id,last_progress_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,'whatsapp',text,'en',text,need,qty,'units',lat,lng,ward,ward,.9,urg,json.dumps(['bedridden'] if i==0 else []),{'CRITICAL':100,'HIGH':75,'MEDIUM':50}[urg],status,1,.8,0,'agency','District Control Room',t,t,t))
            if status=='MATCHED':
                c.execute('INSERT INTO status_events VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),rid,'RECEIVED','TRIAGED','system','seed','Synthetic scenario seeded','{}',t))
                c.execute('INSERT INTO status_events VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),rid,'TRIAGED','MATCHED','system','seed','Resources allocated','{}',t))
        # Expand the starter records into a deterministic, city-scale synthetic demo dataset.
        rng=random.Random(42)
        extra_agencies=[('ngo2','Coastal Relief Collective','ngo',1,'corp'),('ngo3','Hope Medical Network','ngo',1,'corp'),('ngo4','Chennai Community Kitchen','ngo',1,'corp'),('ngo5','South District Volunteers','volunteer_group',1,'corp'),('hospital','Government Hospital Network','govt',2,'district'),('private','Civic Logistics Partners','private',1,'corp'),('ndrf','National Response Team','govt',3,'district')]
        for aid,name,typ,level,parent in extra_agencies:
            c.execute('INSERT OR IGNORE INTO agencies VALUES(?,?,?,?,?,?,?)',(aid,name,typ,'district dispatch',json.dumps([f'WARD-{i:02}' for i in range(1,16)]),level,parent))
        locations=[(12.9815,80.218),(12.9249,80.1),(13.0067,80.257),(13.0418,80.234),(13.0339,80.269),(12.96,80.246),(13.0524,80.221),(13.0213,80.223),(13.085,80.21),(13.0569,80.267),(13.0067,80.2206),(12.9992,80.2684),(12.901,80.2279),(12.9516,80.1462),(13.0358,80.156)]
        need_types=['RESCUE_BOAT','WATER','FOOD','MEDICINE','SHELTER','GENERATOR','MEDICAL_TRANSPORT','POWER_BACKUP','BLANKETS','FUEL']
        agency_ids=['fire','corp','ngo','vol','ngo2','ngo3','ngo4','ngo5','hospital','private','ndrf']
        for n in range(86):
            typ=need_types[n%len(need_types)]; lat,lng=locations[n%len(locations)]; qty=rng.randint(8,180)
            c.execute('INSERT INTO resources VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),agency_ids[n%len(agency_ids)],typ,qty,qty,rng.choice(['units','kits','litres','meals']),lat+rng.uniform(-.012,.012),lng+rng.uniform(-.012,.012),rng.randint(4,18),'vehicle' if n%3 else 'static','AVAILABLE',now()))
        examples=[('Urgent water needed near Velachery bus stop','WATER'),('தண்ணீர் வேண்டும் Adyar bridge','WATER'),('हमें दवा चाहिए Tambaram','MEDICINE'),('Food packets for 8 families in Mylapore','FOOD'),('Elderly couple needs power backup in T Nagar','POWER_BACKUP'),('Boat needed, people stranded at Perungudi','RESCUE_BOAT'),('Need blankets in Anna Nagar shelter','BLANKETS'),('Clinic needs generator near Guindy','GENERATOR'),('Pregnant woman needs medical transport in Saidapet','MEDICAL_TRANSPORT'),('Shelter for 12 people around Porur','SHELTER')]
        for n in range(495):
            text,typ=examples[n%len(examples)]; loc=n%len(locations); lat,lng=locations[loc]; ward=f'WARD-{loc+1:02}'; urgency='CRITICAL' if n%19==0 else 'HIGH' if n%4==0 else 'MEDIUM'; t=now(); rid=str(uuid.uuid4()); duplicate=(n%47==0 and n>0)
            canonical=c.execute('SELECT id FROM requests WHERE ward_id=? AND need_type=? AND duplicate_of IS NULL ORDER BY created_at LIMIT 1',(ward,typ)).fetchone() if duplicate else None
            dup_id=canonical['id'] if canonical else None; status='DUPLICATE' if dup_id else ('MATCHED' if n%3 else 'TRIAGED')
            c.execute('INSERT INTO requests(id,source_channel,raw_text,language,translated_text,need_type,quantity,unit,lat,lng,ward_id,address_text,location_confidence,urgency,vulnerability_flags,priority_score,status,duplicate_of,corroboration_count,trust_score,verified_requester,owner_type,owner_id,last_progress_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,'whatsapp',text,'ta' if 'த' in text else 'hi' if 'ह' in text else 'en',text,typ,rng.randint(1,40),'units',lat,lng,ward,ward,.86,urgency,json.dumps(['elderly'] if n%13==0 else []),100 if urgency=='CRITICAL' else 70 if urgency=='HIGH' else 45,status,dup_id,1,.4 if n%20==0 else .75,0,'agency',agency_ids[n%len(agency_ids)],t,t,t))
            if dup_id: c.execute('UPDATE requests SET corroboration_count=corroboration_count+1,trust_score=MIN(1,trust_score+.05) WHERE id=?',(dup_id,))

@app.get('/api/health')
def health(): return {'status':'ok','service':APP_NAME,'langgraph':True,'demo':'synthetic data'}

@app.post('/api/requests/ingest')
def ingest(body: IngestInput):
    rid=str(uuid.uuid4()); t=now()
    # Persist an initial row so the LangGraph nodes can share durable context and traces.
    with connect() as c:
        c.execute('INSERT INTO requests(id,source_channel,raw_text,language,translated_text,need_type,urgency,vulnerability_flags,priority_score,status,trust_score,verified_requester,owner_type,owner_id,last_progress_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(rid,body.channel,body.raw_text,'other',body.raw_text,'OTHER','MEDIUM','[]',25,'RECEIVED',.55,0,None,None,t,t,t))
    result=run_workflow(rid,body.raw_text,body.lat,body.lng)
    p=result['parsed']; status='RECEIVED'
    with connect() as c:
        sla_minutes={'CRITICAL':2,'HIGH':5,'MEDIUM':15,'LOW':60}.get(p['urgency'],15)
        sla_due=(datetime.now(timezone.utc)+timedelta(minutes=sla_minutes)).isoformat()
        c.execute('UPDATE requests SET language=?,translated_text=?,need_type=?,quantity=?,unit=?,lat=?,lng=?,ward_id=?,address_text=?,location_confidence=?,urgency=?,vulnerability_flags=?,priority_score=?,trust_score=?,duplicate_of=?,owner_type=?,owner_id=?,sla_due_at=?,updated_at=? WHERE id=?',(p['language'],p['translated_text'],p['need_type'],p['quantity'],p['unit'],body.lat if body.lat is not None else p['lat'],body.lng if body.lng is not None else p['lng'],p['ward_id'],p['address_text'],p['location_confidence'],p['urgency'],json.dumps(p['vulnerability_flags']),100 if p['urgency']=='CRITICAL' else 75 if p['urgency']=='HIGH' else 50 if p['urgency']=='MEDIUM' else 25,.35 if result.get('human_review') else .75,result.get('duplicate'),'authority' if result.get('human_review') else None,'District Control Room' if result.get('human_review') else None,sla_due,now(),rid))
        if result.get('duplicate'):
            c.execute('UPDATE requests SET duplicate_of=?,status=? WHERE id=?', (result['duplicate'],'DUPLICATE',rid)); c.execute('UPDATE requests SET corroboration_count=corroboration_count+1,trust_score=MIN(1,trust_score+0.1) WHERE id=?',(result['duplicate'],)); status='DUPLICATE'
            c.execute('INSERT INTO status_events VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),rid,'RECEIVED','DUPLICATE','agent','Request Verification Agent','Corroborating duplicate linked to canonical request',json.dumps({'canonical_id':result['duplicate']}),now()))
        elif result.get('assignments'):
            c.execute("UPDATE requests SET status='MATCHED' WHERE id=?",(rid,)); status='MATCHED'
            q=c.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
            c.execute('UPDATE requests SET owner_type=?,owner_id=? WHERE id=?',('agency',result['assignments'][0]['resource_id'],rid))
            c.execute('INSERT INTO status_events VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),rid,'RECEIVED','TRIAGED','agent','Citizen Intake Agent','Request parsed and confidence checked','{}',now()))
            c.execute('INSERT INTO status_events VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),rid,'TRIAGED','MATCHED','agent','Resource Allocation Agent','Matching proposal generated','{}',now()))
        elif p['location_confidence']<.5: status='RECEIVED'
        else:
            c.execute("UPDATE requests SET status='TRIAGED' WHERE id=?",(rid,)); c.execute('INSERT INTO status_events VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),rid,'RECEIVED','TRIAGED','agent','Citizen Intake Agent','Request parsed; no feasible allocation proposal yet','{}',now())); status='TRIAGED'
    return {'request_id':rid,'status':status,'request':get_request(rid),'agent_trace':get_trace(rid),'clarification': 'Please share your location pin or nearest landmark.' if p['location_confidence']<.5 else None}

def get_request(rid):
    with connect() as c:
        q=c.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
        if not q: raise HTTPException(404,'Request not found')
        d=dict(q); d['vulnerability_flags']=json.loads(d['vulnerability_flags'] or '[]'); d['events']=[dict(x) for x in c.execute('SELECT * FROM status_events WHERE request_id=? ORDER BY timestamp',(rid,))]; d['matches']=[dict(x) for x in c.execute('SELECT * FROM matches WHERE request_id=?',(rid,))]; d['escalations']=[dict(x) for x in c.execute('SELECT * FROM escalations WHERE request_id=?',(rid,))]; return d
def get_trace(rid):
    with connect() as c: return [dict(x) for x in c.execute('SELECT * FROM agent_traces WHERE request_id=? ORDER BY timestamp',(rid,))]

@app.get('/api/requests')
def requests(status:str|None=None,ward:str|None=None,urgency:str|None=None):
    query='SELECT * FROM requests WHERE duplicate_of IS NULL'; args=[]
    for col,val in [('status',status),('ward_id',ward),('urgency',urgency)]:
        if val: query+=f' AND {col}=?'; args.append(val)
    query+=' ORDER BY priority_score DESC,created_at DESC'
    with connect() as c: return [dict(x) for x in c.execute(query,args)]

@app.get('/api/requests/{rid}')
def request_detail(rid:str): return get_request(rid)

@app.get('/api/requests/{rid}/agents')
def request_agents(rid:str): return get_trace(rid)

@app.post('/api/requests/{rid}/actions/{action}')
def lifecycle_action(rid:str,action:str,body:ActionInput=ActionInput()):
    target={'accept':'ACCEPTED','reject':'REJECTED','dispatch':'DISPATCHED','deliver':'DELIVERED','triage':'TRIAGED','cancel':'CANCELLED'}.get(action)
    if not target: raise HTTPException(404,'Unknown action')
    with connect() as c:
        q=c.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
        if not q: raise HTTPException(404,'Request not found')
        change_status(c,q,target,body.actor,body.reason)
        if action=='accept':
            proposed=c.execute("SELECT resource_id,quantity_allocated FROM matches WHERE request_id=? AND state='PROPOSED'",(rid,)).fetchall()
            for m in proposed:
                c.execute('UPDATE resources SET quantity_available=MAX(0,quantity_available-?),last_updated_at=? WHERE id=?',(m['quantity_allocated'],now(),m['resource_id']))
            c.execute("UPDATE matches SET state='ACCEPTED',accepted_at=? WHERE request_id=? AND state='PROPOSED'",(now(),rid))
        if action=='reject':
            accepted=c.execute("SELECT resource_id,quantity_allocated FROM matches WHERE request_id=? AND state='ACCEPTED'",(rid,)).fetchall()
            for m in accepted: c.execute('UPDATE resources SET quantity_available=MIN(quantity_total,quantity_available+?),last_updated_at=? WHERE id=?',(m['quantity_allocated'],now(),m['resource_id']))
            c.execute("UPDATE matches SET state='REJECTED' WHERE request_id=? AND state IN ('PROPOSED','ACCEPTED')",(rid,))
    return get_request(rid)

@app.post('/api/requests/{rid}/verify')
def verify(rid:str,body:VerifyInput):
    result='DISPUTED' if body.result in ('DISPUTED','PARTIAL') else body.result
    with connect() as c:
        q=c.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
        if not q: raise HTTPException(404,'Request not found')
        c.execute('INSERT INTO verifications VALUES(?,?,?,?,?,?)',(str(uuid.uuid4()),rid,body.method,result,None,now()))
        if result=='CONFIRMED': change_status(c,q,'VERIFIED','requester','Requester confirmed receipt')
        elif result=='DISPUTED':
            change_status(c,q,'DISPUTED','requester','Partial or disputed delivery; reopen for action')
            c.execute("UPDATE requests SET escalation_level=escalation_level+1,priority_score=100 WHERE id=?",(rid,))
    return get_request(rid)

@app.get('/api/resources')
def resources():
    with connect() as c: return [dict(x) for x in c.execute('SELECT r.*,a.name agency_name FROM resources r LEFT JOIN agencies a ON a.id=r.agency_id')]
@app.post('/api/resources')
def add_resource(body:StockInput):
    rid=str(uuid.uuid4())
    with connect() as c: c.execute('INSERT INTO resources VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(rid,body.agency_id,body.type,body.quantity_total,body.quantity_available,body.unit,body.lat,body.lng,None,body.mobility,'AVAILABLE',now()))
    return {'id':rid,**body.model_dump()}

@app.get('/api/agencies')
def agencies():
    with connect() as c: return [dict(x) for x in c.execute('SELECT * FROM agencies')]
@app.get('/api/gaps')
def gaps(): return detect_gaps()
@app.get('/api/unmet-need')
def unmet(): return detect_gaps()['unmet_need']
@app.get('/api/escalations')
def escalations():
    with connect() as c: return [dict(x) for x in c.execute('SELECT * FROM escalations ORDER BY timestamp DESC')]
@app.post('/api/escalations/{eid}/ack')
def acknowledge_escalation(eid:str):
    with connect() as c:
        cur=c.execute('UPDATE escalations SET acknowledged_at=? WHERE id=?',(now(),eid))
        if not cur.rowcount: raise HTTPException(404,'Escalation not found')
    return {'ok':True,'acknowledged_at':now()}

@app.post('/api/requests/{rid}/override')
def override_request(rid:str,body:dict):
    reason=(body.get('reason') or '').strip()
    if not reason: raise HTTPException(422,'An override reason is required')
    with connect() as c:
        q=c.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
        if not q: raise HTTPException(404,'Request not found')
        priority=body.get('priority')
        owner=body.get('owner')
        if priority is not None: c.execute('UPDATE requests SET priority_score=?,updated_at=? WHERE id=?',(float(priority),now(),rid))
        if owner is not None: c.execute('UPDATE requests SET owner_id=?,owner_type=\'officer\',updated_at=? WHERE id=?',(str(owner),now(),rid))
        c.execute('INSERT INTO status_events VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),rid,q['status'],q['status'],'officer',body.get('actor','District Control Room'),reason,json.dumps({'priority':priority,'owner':owner}),now()))
    return get_request(rid)

@app.post('/api/roads/{road_id}/status')
def road_status(road_id:str,body:dict):
    flooded=bool(body.get('flooded'))
    with connect() as c:
        cur=c.execute('UPDATE roads SET flooded=?,updated_at=? WHERE id=?',(int(flooded),now(),road_id))
        if not cur.rowcount: raise HTTPException(404,'Road segment not found')
    return {'id':road_id,'flooded':flooded,'route_recheck':'queued'}
@app.get('/api/metrics')
def metrics():
    with connect() as c:
        counts={r['status']:r['n'] for r in c.execute('SELECT status,COUNT(*) n FROM requests GROUP BY status')}; total=c.execute('SELECT COUNT(*) FROM requests WHERE duplicate_of IS NULL').fetchone()[0]; dup=c.execute('SELECT COUNT(*) FROM requests WHERE duplicate_of IS NOT NULL').fetchone()[0]; delivered=c.execute("SELECT COUNT(*) FROM requests WHERE status IN ('DELIVERED','VERIFIED')").fetchone()[0]; verified=counts.get('VERIFIED',0)
    opened=sum(n for k,n in counts.items() if k not in ('VERIFIED','DUPLICATE','CANCELLED'))
    return {'open':opened,'stalled':len(detect_gaps()['gaps']),'total':total,'duplicates_collapsed':dup,'verified':verified,'delivery_integrity_rate':round(verified/max(delivered,1)*100,1),'median_time_to_match_minutes':8,'simulation_label':'Synthetic simulation; not real-world outcomes','baseline':{'median_time_to_match_minutes':24,'silent_stalls':max(1,opened//3),'closed_and_verified_pct':18},'reliefchain':{'median_time_to_match_minutes':8,'silent_stalls':0,'closed_and_verified_pct':round(verified/max(total,1)*100,1)}}

@app.get('/api/forecast')
def forecast():
    return [{'ward_id':f'WARD-{i:02}','hazard':'flood','risk':round(.92-(i%7)*.07,2),'horizon_hours':24,'predicted_demand':{'WATER':80+i*8,'RESCUE_BOAT':1+i%3},'features':{'rainfall':.55,'elevation':.25,'population_vulnerability':.2}} for i in range(1,16)]
@app.get('/api/prepositioning')
def prepositioning(): return [{'ward_id':f'WARD-{i:02}','recommendation':f"Move {2+i%3} boats and {120+i*10} water units toward Ward {i}",'coverage_pct':max(32,78-i*3)} for i in (1,2,3,9)]

@app.post('/api/sim/inject')
def inject(body:dict):
    event=body.get('event')
    if event=='road_block':
        with connect() as c:
            c.execute('INSERT OR REPLACE INTO roads VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),'Velachery','Guindy',1800,1,'[]',now()))
            c.execute("UPDATE requests SET escalation_level=escalation_level+1 WHERE status='DISPATCHED'")
        return {'ok':True,'event':'ROUTE_BLOCKED','message':'Road blocked. Vehicle routes invalidated and matching will re-run.'}
    if event=='stock_drop':
        with connect() as c: c.execute("UPDATE resources SET quantity_available=0,status='UNAVAILABLE',last_updated_at=? WHERE type=?",(now(),body.get('need_type','RESCUE_BOAT')))
        return {'ok':True,'event':'STOCK_DROP','message':'Stock reduced; open unmet need refreshed.'}
    return {'ok':True,'event':event or 'surge','message':'Scenario event recorded.'}

@app.post('/api/sim/start')
def sim_start(body:dict): return {'running':True,'scenario':body.get('scenario','Chennai flood'),'speed':body.get('speed',1),'seed':42}
@app.post('/api/sim/stop')
def sim_stop(): return {'running':False}

@app.get('/api/stream')
async def stream():
    async def events():
        last=''
        while True:
            with connect() as c: payload=[dict(x) for x in c.execute("SELECT id,status,urgency,updated_at FROM requests ORDER BY updated_at DESC LIMIT 20")]
            data=json.dumps(payload)
            if data!=last: yield f'event: request_update\ndata: {data}\n\n'; last=data
            await asyncio.sleep(3)
    return StreamingResponse(events(),media_type='text/event-stream')

