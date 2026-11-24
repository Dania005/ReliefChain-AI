import pytest
from fastapi import HTTPException
from app.state_machine import validate_transition

@pytest.mark.parametrize('source,target',[('RECEIVED','TRIAGED'),('TRIAGED','MATCHED'),('MATCHED','ACCEPTED'),('ACCEPTED','DISPATCHED'),('DISPATCHED','DELIVERED'),('DELIVERED','VERIFIED')])
def test_happy_path_transitions(source,target):
    validate_transition(source,target)

def test_illegal_transition_is_conflict():
    with pytest.raises(HTTPException) as e: validate_transition('RECEIVED','DISPATCHED')
    assert e.value.status_code==409
