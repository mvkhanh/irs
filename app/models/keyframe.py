from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import Annotated, List


class ObjectCount(BaseModel):
    name: str = Field(..., description="Tên object, ví dụ: 'person'")
    count: int = Field(..., ge=0, description="Số lượng object trong keyframe")


class Keyframe(Document):
    key: Annotated[int, Indexed(unique=True)]            # id
    video_num: Annotated[int, Indexed()]                 # V001
    group_num: Annotated[int, Indexed()]                 # L21
    keyframe_num: Annotated[int, Indexed()]              # 000123.webp
    objects: List[ObjectCount] = Field(default_factory=list)

    class Settings:
        name = "keyframes"
        # Indexes cho filter nhanh theo object
        indexes = [
            [("objects.name", 1)],                                  # tìm theo tên object
            [("objects.name", 1), ("objects.count", 1)],            # tìm theo tên + số lượng
            [("video_num", 1), ("group_num", 1), ("keyframe_num", 1)]
        ]