"""Optional OpenAI-compatible structured extraction. Never used without an explicit key."""
import json, os, urllib.request

class RealLLM:
    def __init__(self):
        self.api_key=os.getenv('OPENAI_API_KEY','')
        self.endpoint=os.getenv('LLM_BASE_URL','https://api.openai.com/v1/chat/completions')
        self.model=os.getenv('LLM_MODEL','gpt-4o-mini')
        if not self.api_key: raise RuntimeError('OPENAI_API_KEY is not configured')

    def extract_request(self,text:str,lat:float|None=None,lng:float|None=None)->dict:
        schema={'need_type':'string enum','quantity':'number or null','unit':'string or null','urgency':'CRITICAL|HIGH|MEDIUM|LOW','address_text':'string or null','language':'ta|hi|en|other','vulnerability_flags':'array','translated_text':'string','location_confidence':'number 0..1','ward_id':'string or null','lat':'number or null','lng':'number or null','confidence':'number 0..1'}
        body={'model':self.model,'temperature':0,'response_format':{'type':'json_object'},'messages':[{'role':'system','content':'Extract emergency request fields. Never invent location or quantity. Return only JSON matching this shape: '+json.dumps(schema)},{'role':'user','content':json.dumps({'text':text,'pin':{'lat':lat,'lng':lng}})}]}
        req=urllib.request.Request(self.endpoint,data=json.dumps(body).encode(),headers={'Authorization':f'Bearer {self.api_key}','Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=12) as response: data=json.loads(response.read())
        parsed=json.loads(data['choices'][0]['message']['content'])
        if not isinstance(parsed,dict) or parsed.get('need_type') not in {'WATER','FOOD','MEDICINE','SHELTER','RESCUE_BOAT','MEDICAL_TRANSPORT','GENERATOR','POWER_BACKUP','COOLING','BLANKETS','FUEL','OTHER'}: raise ValueError('Invalid structured extraction')
        if parsed.get('quantity') is not None and float(parsed['quantity'])<0: raise ValueError('Negative quantity is invalid')
        return parsed
