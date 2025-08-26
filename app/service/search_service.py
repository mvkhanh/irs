import os
import sys
import math
ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '../'
    )
)
sys.path.insert(0, ROOT_DIR)

from repository.milvus import KeyframeVectorRepository
from repository.milvus import MilvusSearchRequest
from repository.mongo import KeyframeRepository
from schema.interface import MongoSearchResult, MongoSearchRequest
from schema.response import KeyframeServiceReponse
from schema.request import ImageSearchRequest, UnifiedSearchRequest

def rrf(ranks: dict[int, int], k: int = 60) -> dict[int, float]:
    # Reciprocal Rank Fusion
    return {i: 1.0 / (k + r) for i, r in ranks.items()}

class KeyframeQueryService:
    def __init__(
            self, 
            keyframe_vector_repo: KeyframeVectorRepository,
            keyframe_mongo_repo: KeyframeRepository,
            data_folder: str  
        ):

        self.keyframe_vector_repo = keyframe_vector_repo
        self.keyframe_mongo_repo= keyframe_mongo_repo
        self.data_folder = data_folder

    def get_total(self):
        return self.keyframe_vector_repo.get_total()
    
    def convert_model_to_path(
            self,
            model: MongoSearchResult
        ) -> tuple[int, str]:
            return model.key, os.path.join(self.data_folder, f'Keyframes_L{model.group_num:02d}', f'L{model.group_num:02d}_V{model.video_num:03d}', f'{model.keyframe_num:03d}.jpg')
        
    async def get_keyframes(self, req: MongoSearchRequest) -> list[KeyframeServiceReponse]:
        results = await self.keyframe_mongo_repo.get_keyframe(req)
        return results

    async def image_search(self, search_request: ImageSearchRequest) -> list[KeyframeServiceReponse]:
        search_results = await self.keyframe_vector_repo.search_by_img_id(search_request)
        
        sorted_results = sorted(
            search_results.results, key=lambda r: r.distance, reverse=True
        )

        sorted_ids = [result.id_ for result in sorted_results]

        keyframes = await self.get_keyframes(MongoSearchRequest(keys=sorted_ids))

        return list(map(lambda pair: KeyframeServiceReponse(id=pair[0], path=pair[1]), map(self.convert_model_to_path, keyframes)))

    async def get_neighbors(self, imgid: int, k: int):
        range_search = [imgid + i for i in range(-k, k + 1)]
        results = await self.get_keyframes(MongoSearchRequest(keys=range_search))
        results = [r for r in results if r.video_num == results[k].video_num and r.group_num == results[k].group_num]
        return list(map(lambda pair: KeyframeServiceReponse(id=pair[0], path=pair[1]), map(self.convert_model_to_path, results)))
    
    async def unified_search(self, text_emb: list[float] | None, req: UnifiedSearchRequest):
        cand_ids: set[int] = set()
        scores_vec: dict[int, float] = {}
        scores_asr: dict[int, float] = {}
        scores_ocr: dict[int, float] = {}

        # 1) Vector ANN (nếu có query)
        if text_emb is not None:
            top_n = max(req.size * req.page * req.oversample, req.size * req.oversample)
            vec_req = MilvusSearchRequest(embedding=text_emb, top_k=top_n, exclude_ids=req.exclude_ids or [])
            res = await self.keyframe_vector_repo.search_by_embedding(vec_req)
            # sắp theo distance phù hợp metric (giữ nguyên thứ tự từ Milvus cũng OK)
            sorted_res = sorted(res.results, key=lambda r: r.distance, reverse=True)
            vec_ids = [int(r.id_) for r in sorted_res]

            cand_ids.update(vec_ids)

            # rank→RRF score
            ranks = {i: r for r, i in enumerate(vec_ids, start=1)}
            scores_vec = rrf(ranks)

        # 2) FTS ASR (SpeechCaption.text) → time ranges → keyframe ids
        if req.asr:
            segs = await self.keyframe_mongo_repo.fts_search(source='asr', text=req.asr, return_type='segments', limit=1000)
            ranges = []
            for s in segs:
                # Convert seconds to keyframe_num range (fps = 30)
                kfs = int(s.get("start", 0) * 30)
                kfe = int(math.ceil(s.get("end", 0) * 30))
                ranges.append((int(s["group_num"]), int(s["video_num"]), kfs, kfe))
            asr_ids = await self.keyframe_mongo_repo.key_ids_in_time_ranges(ranges, per_range_limit=10)
            cand_ids.update(asr_ids)
            # rank by appearance order (RRF later combines with other signals)
            ranks = {i: r for r, i in enumerate(asr_ids, start=1)}
            scores_asr = rrf(ranks)

        # 3) FTS OCR (Keyframe.ocr via fts_ids)
        if req.ocr:
            ocr_pairs = await self.keyframe_mongo_repo.fts_search("ocr", req.ocr, return_type='ids', limit=5000)
            ocr_ids = [i for i, _ in ocr_pairs]
            cand_ids.update(ocr_ids)
            ranks = {i: r for r, i in enumerate(ocr_ids, start=1)}
            scores_ocr = rrf(ranks)

        # 5) Hợp nhất điểm (weighted)
        def score_of(i: int) -> float:
            return (
                req.w_vec * scores_vec.get(i, 0.0)
                + req.w_asr * scores_asr.get(i, 0.0)
                + req.w_ocr * scores_ocr.get(i, 0.0)
            )
        ranked = []
        
        if cand_ids:
            ranked = sorted(cand_ids, key=lambda i: (score_of(i), i), reverse=True)

        if req.obj_filters:
            ranked = await self.keyframe_mongo_repo.filter_by_objects_list(ranked, req.obj_filters)
            
        keyframes = await self.get_keyframes(MongoSearchRequest(keys=ranked, group_nums=req.group_nums, video_nums=req.video_nums, page=req.page, size=req.size))

        res = []
        for kf in keyframes:
            id_, path = self.convert_model_to_path(kf)
            res.append(KeyframeServiceReponse(id=id_, path=path))
        return res