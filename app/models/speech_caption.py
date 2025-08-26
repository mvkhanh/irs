from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import Annotated, List
from pymongo import IndexModel, TEXT, ASCENDING

class SpeechCaption(Document):
    # seg_id: Annotated[int, Indexed(unique=True)] # Mapping for milvus dense search
    group_num: int
    video_num: int
    start: float
    end: float
    text: str
    
    class Settings:
        name='speech_captions'
        
        indexes = [
            IndexModel([("text", TEXT)], name="fts_text", default_language="none"),
            IndexModel([("group_num", ASCENDING), ("video_num", ASCENDING), ("start", ASCENDING), ("end", ASCENDING)],
                       name="video_time"),
        ]