class SimWhatsApp:
    """In-app WhatsApp-shaped simulator. A real provider can implement this interface later."""
    def receive(self,message:dict)->dict:
        return {'channel':'whatsapp','raw_text':message.get('text',''),'sender':message.get('sender'),'lat':message.get('lat'),'lng':message.get('lng')}
    def send(self,to:str,text:str,buttons:list[str]|None=None)->dict:
        return {'to':to,'text':text,'buttons':buttons or [],'simulated':True}
