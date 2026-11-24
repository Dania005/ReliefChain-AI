from app.ai.mock_llm import extract

def test_multilingual_need_and_urgency():
    parsed=extract('Appa ku oxygen cylinder venum, Velachery 2nd main road, tanni vandhuduchi')
    assert parsed['need_type']=='MEDICAL_TRANSPORT'
    assert parsed['urgency']=='CRITICAL'
    assert parsed['address_text']=='Velachery'

def test_missing_location_stays_unknown():
    parsed=extract('Need food for people urgently')
    assert parsed['lat'] is None and parsed['lng'] is None
    assert parsed['location_confidence']<.5
