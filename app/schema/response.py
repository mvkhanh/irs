from pydantic import BaseModel, Field


class KeyframeServiceReponse(BaseModel):
    id: int
    path: str
        
class KeyframeDisplay(BaseModel):
    total_page: int
    results: list[KeyframeServiceReponse]