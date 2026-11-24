import logging
logger=logging.getLogger(__name__)

class SMSStub:
    """Offline SMS adapter stub. Replace send() with Twilio/provider transport when configured."""
    def receive(self,message:dict)->dict: return {'channel':'sms','raw_text':message.get('text',''),'sender':message.get('sender')}
    def send(self,to:str,text:str,buttons:list[str]|None=None)->dict:
        logger.info('sms_simulated',extra={'to_masked':to[-3:].rjust(len(to),'*') if to else None,'message':text})
        return {'to':to,'text':text,'simulated':True}
