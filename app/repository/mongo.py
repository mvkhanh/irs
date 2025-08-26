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

from typing import List, Tuple, Literal, Optional, Any
from models.keyframe import Keyframe
from models.speech_caption import SpeechCaption
from common.repository import MongoBaseRepository
from schema.interface import MongoSearchResult, MongoSearchRequest
from schema.request import ObjFilter
MAX_PAGE_SIZE = 200
class KeyframeRepository(MongoBaseRepository[Keyframe]):
    
    async def get_keyframe(self, search_request: MongoSearchRequest):
        col = Keyframe.get_pymongo_collection()

        # --- $match ---
        q: dict = {}
        if search_request.keyframe_nums:
            q["keyframe_num"] = {"$in": search_request.keyframe_nums}

        and_conds = []
        if search_request.group_nums and search_request.video_nums:
            pairs = []
            for g, v in zip(search_request.group_nums, search_request.video_nums):
                if v != -1:
                    pairs.append({"group_num": g, "video_num": v})
                else:
                    pairs.append({"group_num": g})
            and_conds.append({"$or": pairs})
        elif search_request.group_nums:
            q["group_num"] = {"$in": search_request.group_nums}
        elif search_request.video_nums:
            q["video_num"] = {"$in": search_request.video_nums}

        if and_conds:
            q["$and"] = and_conds

        page = max(1, (search_request.page or 1))
        size = min(MAX_PAGE_SIZE, max(1, (search_request.size or 50)))
        skip = (page - 1) * size

        pipeline = [{"$match": q}]

        if search_request.keys:
            # chỉ lấy các doc có trong keys & sắp theo thứ tự keys truyền vào
            pipeline += [
                {"$match": {"key": {"$in": search_request.keys}}},
                {"$addFields": {"__order": {"$indexOfArray": [search_request.keys, "$key"]}}},
                {"$match": {"__order": {"$ne": -1}}},
                {"$sort": {"__order": 1}},
            ]
        else:
            pipeline += [{"$sort": {"group_num": 1, "video_num": 1, "keyframe_num": 1}}]

        pipeline += [
            {"$skip": skip},
            {"$limit": size},
            {"$project": {
                "_id": 0,
                "key": 1,
                "video_num": 1,
                "group_num": 1,
                "keyframe_num": 1
            }},
        ]

        docs = await col.aggregate(pipeline).to_list(length=None)
        return [MongoSearchResult(**d) for d in docs]
    
    async def fts_search(
        self,
        source: Literal['asr', 'ocr'],
        text: str,
        *,
        return_type: Literal['ids', 'segments'] = 'ids',
        limit: int = 5000,
        atlas_index: str = 'default',
        field_override: Optional[str] = None,
    ) -> List[Any]:
        """
        Full-text search hợp nhất cho ASR/OCR.

        Params:
        - source: 'asr' (SpeechCaption) hoặc 'ocr' (Keyframe).
        - text: chuỗi truy vấn.
        - return_type:
            'ids'      -> trả [(key:int, score:float)]
            'segments' -> trả list dict {group_num, video_num, start, end, score}
        - limit: số lượng kết quả tối đa.
        - atlas_index: tên index Atlas Search.
        - field_override: override field tìm kiếm (mặc định: asr->'text', ocr->'ocr').

        Thứ tự tìm kiếm:
        1) Atlas Search ($search)
        2) Mongo $text với meta score
        3) Regex fallback (không có score -> 1.0)
        """
        # Chọn collection & field mặc định
        if source == 'asr':
            col = SpeechCaption.get_pymongo_collection()
            field = field_override or 'text'
        else:
            col = Keyframe.get_pymongo_collection()
            field = field_override or 'ocr'

        # ========== 1) Atlas Search ==========
        try:
            if return_type == 'ids':
                pipeline = [
                    {"$search": {"index": atlas_index, "text": {"path": field, "query": text}}},
                    {"$limit": limit},
                    {"$project": {"_id": 0, "key": 1, "score": {"$meta": "searchScore"}}},
                ]
                docs = await col.aggregate(pipeline).to_list(length=None)
                if docs:
                    return [(int(d["key"]), float(d["score"])) for d in docs if "key" in d]
            else:  # segments
                pipeline = [
                    {"$search": {"index": atlas_index, "text": {"path": field, "query": text}}},
                    {"$limit": min(limit, 1000)},  # giữ behavior cũ cho segments
                    {"$project": {
                        "_id": 0,
                        "group_num": 1,
                        "video_num": 1,
                        "start": 1,
                        "end": 1,
                        "score": {"$meta": "searchScore"},
                    }},
                ]
                docs = await col.aggregate(pipeline).to_list(length=None)
                if docs:
                    return docs
        except Exception:
            pass

        # ========== 2) $text meta score ==========
        try:
            q = {"$text": {"$search": text}}
            if return_type == 'ids':
                proj = {"_id": 0, "key": 1, "score": {"$meta": "textScore"}}
                cur = col.find(q, proj).sort([("score", {"$meta": "textScore"})]).limit(limit)
                docs = await cur.to_list(length=None)
                if docs:
                    return [(int(d["key"]), float(d["score"])) for d in docs if "key" in d]
            else:
                proj = {
                    "_id": 0,
                    "group_num": 1,
                    "video_num": 1,
                    "start": 1,
                    "end": 1,
                    "score": {"$meta": "textScore"},
                }
                cur = col.find(q, proj).sort([("score", {"$meta": "textScore"})]).limit(min(limit, 1000))
                docs = await cur.to_list(length=None)
                if docs:
                    return docs
        except Exception:
            pass

        # ========== 3) Regex fallback ==========
        rx = {"$regex": text, "$options": "i"}
        if return_type == 'ids':
            docs = await col.find({field: rx}, {"_id": 0, "key": 1}).limit(limit).to_list(length=None)
            return [(int(d["key"]), 1.0) for d in docs if "key" in d]
        else:
            docs = await col.find(
                {field: rx},
                {"_id": 0, "group_num": 1, "video_num": 1, "start": 1, "end": 1}
            ).limit(min(limit, 1000)).to_list(length=None)
            for d in docs:
                d["score"] = 1.0
            return docs

    async def key_ids_in_time_ranges(
        self,
        ranges: List[Tuple[int, int, int, int]],
        per_range_limit: int = 100
    ) -> List[int]:
        """
        Given a list of tuples (group_num, video_num, kf_start, kf_end),
        return ~evenly spaced keyframe keys within these ranges,
        ordered by keyframe_num asc per range (de-duplicated across ranges).
        """
        col = Keyframe.get_pymongo_collection()
        out: List[int] = []
        seen = set()

        for g, v, kfs, kfe in ranges:
            q = {
                "group_num": g,
                "video_num": v,
                "keyframe_num": {"$gte": int(kfs), "$lte": int(kfe)}
            }

            # Đếm trước để chọn số bucket hợp lệ
            try:
                n = await col.count_documents(q)
            except Exception:
                n = 0

            if n == 0:
                continue

            buckets = max(1, min(per_range_limit, n))

            # --- Cách 1: server-side ($bucketAuto) ---
            try:
                pipeline = [
                    {"$match": q},
                    {"$sort": {"keyframe_num": 1}},
                    {
                        "$bucketAuto": {
                            "groupBy": "$keyframe_num",
                            "buckets": buckets,
                            "output": {
                                "doc": {"$first": "$$ROOT"}  # lấy phần tử đầu của mỗi bucket
                            },
                        }
                    },
                    {"$replaceRoot": {"newRoot": "$doc"}},
                    {"$project": {"_id": 0, "key": 1, "keyframe_num": 1}},
                    {"$sort": {"keyframe_num": 1}},
                ]
                docs = await col.aggregate(pipeline).to_list(length=None)

            except Exception:
                # --- Cách 2: fallback client-side sampling theo linspace ---
                docs_all = await col.find(
                    q, {"_id": 0, "key": 1, "keyframe_num": 1}
                ).sort([("keyframe_num", 1)]).to_list(length=None)

                m = len(docs_all)
                if m <= per_range_limit:
                    docs = docs_all
                else:
                    # chọn chỉ số cách đều 0..m-1 thành per_range_limit điểm
                    idxs = [
                        round(i * (m - 1) / (per_range_limit - 1))
                        for i in range(per_range_limit)
                    ]
                    # loại trùng chỉ số nếu có
                    seen_idx = set()
                    docs = []
                    for ix in idxs:
                        if ix not in seen_idx:
                            seen_idx.add(ix)
                            docs.append(docs_all[ix])

            # Gom kết quả, khử trùng lặp cross-range
            for d in docs:
                k = int(d["key"])
                if k not in seen:
                    seen.add(k)
                    out.append(k)

        return out

    async def filter_by_objects_list(self, ids: List[int], filters: List[ObjFilter]) -> List[int]:
        if not filters: return ids
        ops = {"eq": "$eq", "neq": "$ne", "gt": "$gt", "gte": "$gte", "lt": "$lt", "lte": "$lte"}
        and_conds = []
        for f in filters:
            and_conds.append({"objects": {"$elemMatch": {"name": f.name, "count": {ops[f.cmp]: int(f.count)}}}})
        q = {"key": {"$in": ids}, "$and": and_conds}
        col = Keyframe.get_pymongo_collection()
        docs = await col.find(q, {"_id": 0, "key": 1}).to_list(length=None)
        keep = {int(d["key"]) for d in docs}
        if ids:
            return [i for i in ids if i in keep]
        return list(keep)