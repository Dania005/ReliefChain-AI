from pydantic import BaseModel, Field
from typing import Literal

class IngestInput(BaseModel):
    channel: Literal['whatsapp','sms','call','social','volunteer','web'] = 'web'
    raw_text: str = Field(min_length=3,max_length=4000)
    sender: str | None = None
    lat: float | None = Field(default=None,ge=-90,le=90)
    lng: float | None = Field(default=None,ge=-180,le=180)

class ActionInput(BaseModel):
    reason: str | None = None
    actor: str = 'District Control Room'

class VerifyInput(BaseModel):
    result: Literal['CONFIRMED','DISPUTED','PARTIAL','NO_RESPONSE']
    method: str = 'requester_reply'

class StockInput(BaseModel):
    type: str; quantity_total: int = Field(ge=0); quantity_available: int = Field(ge=0); unit: str = 'units'
    lat: float = 13.02; lng: float = 80.22; agency_id: str | None = None; mobility: str = 'static'

