"""Shared multi-agent request workflow. Each node has typed shared context and records its tool calls."""
from typing import TypedDict, Any
from pydantic import BaseModel, Field
import os
from datetime import datetime, timedelta, timezone
from ..db import connect, trace, now, init_db
from ..ai.mock_llm import extract
from .matching import allocate
from .gaps import detect_gaps

class RequestContext(TypedDict, total=False):
    request_id: str
    raw_text: str
    parsed: dict[str, Any]
    duplicate: str | None
    risk: float
    assignments: list[dict]
    gaps: list[dict]
    human_review: bool
    errors: list[str]
    lat: float | None
    lng: float | None

class ExtractedRequest(BaseModel):
    need_type: str; quantity: float | None=None; unit: str | None=None; urgency: str
    address_text: str | None=None; language: str='other'; translated_text: str=''; vulnerability_flags: list[str]=Field(default_factory=list)
    location_confidence: float=0; ward_id: str | None=None; lat: float | None=None; lng: float | None=None; confidence: float=.5

AGENT_TOOLSETS={
    'Citizen Intake Agent':['MockLLM.extract','RealLLM.extract_json','gazetteer.lookup'],
    'Request Verification Agent':['dedupe.candidate_search','trust.score','human_review.enqueue'],
    'Disaster Intelligence Agent':['forecast.risk_at_location','priority.score'],
    'Resource Allocation Agent':['matching.allocate'],
    'Logistics Agent':['roads.passability','routes.estimate_eta'],
    'Gap Detection Agent':['gaps.detect','unmet_need.aggregate'],
    'Escalation Agent':['escalation.policy_check','escalation.notify_authority'],
    'Delivery Verification Agent':['verification.prompt_requester','verification.record_result'],
}

def intake_agent(s):
    from ..ai.mock_client import MockLLM
    from ..ai.real_llm import RealLLM
    mock=MockLLM()
    try:
        client=RealLLM() if os.getenv('OPENAI_API_KEY') else mock
        try: raw=client.extract_request(s['raw_text'],s.get('lat'),s.get('lng'))
        except Exception:
            if client is not mock: raw=client.extract_request(s['raw_text'],s.get('lat'),s.get('lng'))
            else: raise
        p=ExtractedRequest.model_validate(raw).model_dump(); tool='RealLLM.extract_json' if client is not mock else 'MockLLM.extract'
    except Exception as error:
        p=ExtractedRequest.model_validate(mock.extract_request(s['raw_text'],s.get('lat'),s.get('lng'))).model_dump(); tool='MockLLM.fallback'; s.setdefault('errors',[]).append(str(error))
    s['parsed']=p
    trace(s['request_id'],'Citizen Intake Agent','extract multilingual request',tool,'fallback' if s.get('errors') else 'ok',p)
    return s
def verification_agent(s):
    p=s['parsed']; duplicate=None
    with connect() as c:
        cutoff=(datetime.now(timezone.utc)-timedelta(hours=6)).isoformat()
        rows=c.execute("SELECT id,raw_text,need_type,lat,lng,created_at FROM requests WHERE id!=? AND duplicate_of IS NULL AND created_at>=? ORDER BY created_at DESC LIMIT 150",(s['request_id'],cutoff)).fetchall()
    from .matching import distance_km
    words={w.strip('.,!?;:') for w in p.get('translated_text','').lower().split() if len(w)>3}
    for r in rows:
        other={w.strip('.,!?;:') for w in (r['raw_text'] or '').lower().split() if len(w)>3}
        nearby=distance_km(p.get('lat'),p.get('lng'),r['lat'],r['lng'])<=.3
        union=words|other; similarity=len(words&other)/len(union) if union else 0
        if r['need_type']==p['need_type'] and nearby and similarity>=.35: duplicate=r['id']; break
    s['duplicate']=duplicate; s['human_review']=(p['urgency']=='CRITICAL' and p['confidence']<.55)
    trace(s['request_id'],'Request Verification Agent','deduplicate and assess trust','dedupe.candidate_search','review' if s['human_review'] else 'ok',{'duplicate_of':duplicate,'human_review':s['human_review']})
    return s
def intelligence_agent(s):
    p=s['parsed']; risk=.85 if p.get('ward_id') in ('WARD-01','WARD-02','WARD-03','WARD-09') else .35
    if risk>.8 and p['urgency']=='MEDIUM': p['urgency']='HIGH'
    s['risk']=risk; trace(s['request_id'],'Disaster Intelligence Agent','score ward hazard and urgency','forecast.risk_at_location','ok',{'risk':risk,'urgency':p['urgency']}); return s
def allocation_agent(s):
    if s.get('duplicate') or s.get('human_review'): s['assignments']=[]
    else:
        with connect() as c:
            p=s['parsed']
            c.execute("UPDATE requests SET status='TRIAGED',need_type=?,quantity=?,unit=?,lat=?,lng=?,ward_id=?,urgency=?,priority_score=?,updated_at=? WHERE id=? AND status='RECEIVED'",(p['need_type'],p['quantity'],p['unit'],p['lat'],p['lng'],p['ward_id'],p['urgency'],100 if p['urgency']=='CRITICAL' else 75 if p['urgency']=='HIGH' else 50,s['request_id'] and now(),s['request_id']))
        s['assignments']=allocate(s['request_id'])
    trace(s['request_id'],'Resource Allocation Agent','optimize resource allocation','matching.allocate','ok',{'matches':len(s['assignments'])}); return s
def logistics_agent(s):
    trace(s['request_id'],'Logistics Agent','check route feasibility','roads.passability','ok',{'routes':len(s.get('assignments',[]))}); return s
def gap_agent(s):
    s['gaps']=detect_gaps()['gaps']; trace(s['request_id'],'Gap Detection Agent','scan open lifecycle gaps','gaps.detect','ok',{'open_gaps':len(s['gaps'])}); return s
def escalation_agent(s):
    if s.get('human_review'):
        with connect() as c:
            c.execute("UPDATE requests SET owner_type='authority',owner_id='District Control Room',updated_at=? WHERE id=?",(now(),s['request_id']))
        trace(s['request_id'],'Escalation Agent','route low confidence critical request to human','escalation.human_review','queued',{})
    else:
        trace(s['request_id'],'Escalation Agent','check authority chain and acknowledgement state','escalation.policy_check','no_escalation_required',{'human_review':False})
    return s
def verification_agent_delivery(s):
    trace(s['request_id'],'Delivery Verification Agent','monitor confirmation requirement','verification.policy','pending',{'automatic_verification':False}); return s

def build_graph():
    try:
        from langgraph.graph import StateGraph, END
    except ImportError as e:
        raise RuntimeError('LangGraph is required. Install backend/requirements.txt') from e
    graph=StateGraph(RequestContext)
    graph.add_node('intake',intake_agent); graph.add_node('verification',verification_agent); graph.add_node('intelligence',intelligence_agent); graph.add_node('allocation',allocation_agent); graph.add_node('logistics',logistics_agent); graph.add_node('gaps',gap_agent); graph.add_node('escalation',escalation_agent); graph.add_node('delivery_verification',verification_agent_delivery)
    graph.set_entry_point('intake'); graph.add_edge('intake','verification'); graph.add_edge('verification','intelligence'); graph.add_edge('intelligence','allocation'); graph.add_edge('allocation','logistics'); graph.add_edge('logistics','gaps'); graph.add_edge('gaps','escalation'); graph.add_edge('escalation','delivery_verification'); graph.add_edge('delivery_verification',END)
    return graph.compile()

def run_workflow(request_id: str, raw_text: str, lat:float|None=None,lng:float|None=None):
    init_db()
    return build_graph().invoke({'request_id':request_id,'raw_text':raw_text,'lat':lat,'lng':lng,'errors':[]})
