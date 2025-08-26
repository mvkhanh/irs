from pathlib import Path
import math
import os
import sys
ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '../'
    )
)

sys.path.insert(0, ROOT_DIR)

from service import ModelService, KeyframeQueryService, TranslationService
from schema.response import KeyframeDisplay
from schema.request import (
    ImageSearchRequest,
    UnifiedSearchRequest
)

class QueryController:
    
    def __init__(
        self,
        object_classes_path: Path,
        model_service: ModelService,
        keyframe_service: KeyframeQueryService,
        translate_service: TranslationService
    ):
        self.object_classes_path = object_classes_path
        self.model_service = model_service
        self.keyframe_service = keyframe_service
        self.translate_service = translate_service
        self.total = self.keyframe_service.get_total()
        
    async def get_neighbors(self, imgid: int, k):
        results = await self.keyframe_service.get_neighbors(imgid, k)
        return {'frames': results}
            
    async def image_search(self, search_request: ImageSearchRequest) -> KeyframeDisplay:
        results = await self.keyframe_service.image_search(search_request)
        return KeyframeDisplay(total_page=math.ceil(self.total / search_request.size), results=results)
    
    async def unified_search(self, req: UnifiedSearchRequest) -> KeyframeDisplay:
        emb = None

        if req.query:
            emb = self.model_service.embedding(
                self.translate_service.translate(req.query)
            ).tolist()[0]
        items = await self.keyframe_service.unified_search(emb, req)
        total = math.ceil(self.total / req.size)

        return KeyframeDisplay(total_page=total, results=items)