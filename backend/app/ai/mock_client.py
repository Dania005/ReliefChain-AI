from .llm_base import LLMClient
from .mock_llm import extract

class MockLLM:
    def extract_request(self,text:str,lat:float|None=None,lng:float|None=None)->dict:
        return extract(text,lat,lng)
