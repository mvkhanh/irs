from pathlib import Path
import json
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
    BaseSearchRequest,
    ImageSearchRequest,
    TextSearchRequest
)

class QueryController:
    
    def __init__(
        self,
        data_folder: Path,
        id2index_path: Path,
        object_classes_path: Path,
        model_service: ModelService,
        keyframe_service: KeyframeQueryService,
        translate_service: TranslationService
    ):
        self.data_folder = data_folder # Keyframe folder
        self.id2index = json.load(open(id2index_path, 'r')) # clip2idmap.json
        self.object_classes_path = object_classes_path
        self.model_service = model_service
        self.keyframe_service = keyframe_service
        self.keyframe_service.data_folder = data_folder
        self.translate_service = translate_service
    
    async def get_frames_by_page(self, search_request: BaseSearchRequest) -> KeyframeDisplay:
        results = await self.keyframe_service.get_frames_by_page(search_request)
        return KeyframeDisplay(total_page=math.ceil(len(self.id2index) / search_request.size), results=results)
        
    async def get_neighbors(self, imgid: str, k):
        img_path = self.id2index[imgid]
        # print(img_path)
        video_id = img_path[:-3]
        frames = []
        start = max(0, int(imgid) - k)
        end = min(len(self.id2index), int(imgid) + k + 1)
        for i in range(start, end):
            i = str(i)
            path = self.id2index[i]
            if path[:-3] != video_id:
                continue
            fpath = await self.convert_index_to_path(path)
            frames.append({'id': i, 'imgpath': fpath})
        return {'frames': frames}
            
    async def convert_index_to_path(self, index: str):
        group_id, video_id, img_id = index.split('_')
        return os.path.join(self.data_folder, f'Keyframes_{group_id}', f'{group_id}_{video_id}', f'{img_id}.jpg')
    
    async def image_search(self, search_request: ImageSearchRequest) -> KeyframeDisplay:
        results = await self.keyframe_service.image_search(search_request)
        return KeyframeDisplay(total_page=math.ceil(len(self.id2index) / search_request.size), results=results)
    
    async def text_search(self, search_request: TextSearchRequest) -> KeyframeDisplay:
        embedding = self.model_service.embedding(self.translate_service.translate(search_request.query)).tolist()[0] if search_request.query else None
        results = await self.keyframe_service.search_by_text(embedding, search_request)
        return KeyframeDisplay(total_page=math.ceil(len(self.id2index) / search_request.size), results=results)

