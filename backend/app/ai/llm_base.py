from typing import Protocol, Any

class LLMClient(Protocol):
    def extract_request(self, text: str, lat: float | None=None, lng: float | None=None) -> dict[str, Any]: ...
