from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal

CmpOp = Literal["eq", "neq", "gt", "gte", "lt", "lte"]

class ObjFilter(BaseModel):
    name: str
    cmp: CmpOp
    count: int

class BaseSearchRequest(BaseModel):
    """Base search request with common parameters"""
    size: int = Field(default=100, ge=1, le=500, description="Number of top results to return")
    page: int = Field(default=1, description='Page number')


class TextSearchRequest(BaseSearchRequest):
    """Simple text search request"""
    prev: str | None = Field(default=None, description="Prev query for temporal search", min_length=1, max_length=1000)
    query: str | None = Field(default=None, description="Search query text", min_length=1, max_length=1000)
    next: str | None = Field(default=None, description="Next query for temporal search", min_length=1, max_length=1000)
    ocr: str | None = Field(default=None, description="OCR search", min_length=1, max_length=1000)
    obj_filters: str | None = Field(default=None, description="Object filters")
    oversample: int = Field(default=10, description='Oversample for reranking')
        
class ImageSearchRequest(BaseSearchRequest):
    imgid: int
    

class TextSearchWithExcludeGroupsRequest(BaseSearchRequest):
    """Text search request with group exclusion"""
    exclude_groups: List[int] = Field(
        default_factory=list,
        description="List of group IDs to exclude from search results",
    )


class TextSearchWithSelectedGroupsAndVideosRequest(BaseSearchRequest):
    """Text search request with specific group and video selection"""
    include_groups: List[int] = Field(
        default_factory=list,
        description="List of group IDs to include in search results",
    )
    include_videos: List[int] = Field(
        default_factory=list,
        description="List of video IDs to include in search results",
    )


