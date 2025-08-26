from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from pydantic_core import PydanticUndefined  # <-- thêm dòng này

CmpOp = Literal["eq", "neq", "gt", "gte", "lt", "lte"]

class ObjFilter(BaseModel):
    name: str
    cmp: CmpOp
    count: int

class BaseSearchRequest(BaseModel):
    """Base search request with common parameters"""
    size: int = Field(default=100, ge=1, le=500, description="Number of top results to return")
    page: int = Field(default=1, description='Page number')
   
class ImageSearchRequest(BaseSearchRequest):
    imgid: int
    
class UnifiedSearchRequest(BaseSearchRequest):
    # vector text
    query: str | None = Field(None, min_length=1, max_length=1000)

    # full-text search trên Mongo (ASR/OCR)
    asr: str | None = None
    ocr: str | None = None

    # object filters
    obj_filters: Optional[List[ObjFilter]] = None
    exclude_ids: Optional[List[int]] = None

    group_nums: Optional[List[int]] = None
    video_nums: Optional[List[int]] = None

    # oversample + trọng số trộn
    oversample: int = 10
    w_vec: float = 1.0     # weight vector ANN
    w_asr: float = 1.0     # weight FTS ASR
    w_ocr: float = 0.5     # weight FTS OCR

    # Cho phép nhận obj_filters từ query ?obj_filters=a:gte:2,b:eq:1
    @field_validator("obj_filters", mode="before")
    @classmethod
    def parse_obj_filters(cls, v):
        if v is None or v is PydanticUndefined:
            return []
        # Đã là list[dict]/list[ObjFilter]
        if isinstance(v, list):
            if not v or isinstance(v[0], (dict, ObjFilter)):
                return v
        # Hỗ trợ list[str] hoặc str "a:gte:2,b:eq:1"
        toks: list[str] = []
        if isinstance(v, (list, tuple)):
            for s in v:
                toks += [t for t in str(s).split(",") if t.strip()]
        else:
            toks = [t for t in str(v).split(",") if t.strip()]
        out: list[dict] = []
        for t in toks:
            parts = t.split(":", 2)
            if len(parts) != 3:
                raise ValueError(f"Invalid '{t}', expected name:cmp:count")
            name, cmp_, cnt = parts
            out.append({"name": name, "cmp": cmp_.lower(), "count": int(cnt)})
        return out

    @field_validator("exclude_ids", "group_nums", "video_nums", mode="before")
    @classmethod
    def ensure_list_defaults(cls, v):
        # None / missing -> []
        if v is None or v is PydanticUndefined:
            return []
        return v