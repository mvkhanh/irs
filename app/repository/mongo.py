"""
The implementation of Keyframe repositories. The following class is responsible for getting the keyframe by many ways
"""

import os
import sys
ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '../'
    )
)

sys.path.insert(0, ROOT_DIR)

from typing import Any, List
from models.keyframe import Keyframe
from common.repository import MongoBaseRepository
from schema.interface import KeyframeInterface
from schema.request import BaseSearchRequest
from pydantic import BaseModel
class KeyOnly(BaseModel):
    key: int


class KeyframeRepository(MongoBaseRepository[Keyframe]):
    async def get_keyframe_by_list_of_keys(
        self, keys: list[int]
    ):
        result = await self.find({"key": {"$in": keys}})
        return [
            KeyframeInterface(
                key=keyframe.key,
                video_num=keyframe.video_num,
                group_num=keyframe.group_num,
                keyframe_num=keyframe.keyframe_num
            ) for keyframe in result

        ]

    async def get_keyframe_by_video_num(
        self, 
        video_num: int,
    ):
        result = await self.find({"video_num": video_num})
        return [
            KeyframeInterface(
                key=keyframe.key,
                video_num=keyframe.video_num,
                group_num=keyframe.group_num,
                keyframe_num=keyframe.keyframe_num
            ) for keyframe in result
        ]

    async def get_keyframe_by_keyframe_num(
        self, 
        keyframe_num: int,
    ):
        result = await self.find({"keyframe_num": keyframe_num})
        return [
            KeyframeInterface(
                key=keyframe.key,
                video_num=keyframe.video_num,
                group_num=keyframe.group_num,
                keyframe_num=keyframe.keyframe_num
            ) for keyframe in result
        ]   
    
    async def get_frames_by_page(
        self,
        search_request: BaseSearchRequest
    ) -> List[Keyframe]:
        """
        Lấy danh sách keyframe theo trang.
        """
        skip = (search_request.page - 1) * search_request.size
        result = await self.collection.find_all().skip(skip).limit(search_request.size).to_list()
    
        return [
            KeyframeInterface(key=keyframe.key, video_num=keyframe.video_num, group_num=keyframe.group_num, keyframe_num=keyframe.keyframe_num)
            for keyframe in result
        ]
        
    async def filter_by_objects(self, ids: list[int], obj_filters: str) -> list[int]:
        if not obj_filters or not obj_filters.strip():
            return ids

        ops = {"eq": "$eq", "neq": "$ne", "gt": "$gt", "gte": "$gte", "lt": "$lt", "lte": "$lte"}
        and_conds = []
        for token in obj_filters.split(','):
            name, cmp_, cnt = token.split(':', 2)
            and_conds.append({
                "objects": {"$elemMatch": {"name": name, "count": {ops[cmp_]: int(cnt)}}}
            })

        q = {"key": {"$in": ids}, "$and": and_conds}

        motor_col = Keyframe.get_pymongo_collection()
        docs = await motor_col.find(q, {"_id": 0, "key": 1}).to_list(length=None)

        keep = {d["key"] for d in docs}
        return [i for i in ids if i in keep]