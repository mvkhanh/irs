import os
import sys
ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '../'
    )
)
sys.path.insert(0, ROOT_DIR)


from repository.milvus import KeyframeVectorRepository
from repository.milvus import MilvusSearchRequest
from repository.mongo import KeyframeRepository
from schema.interface import KeyframeInterface
from schema.response import KeyframeServiceReponse
from schema.request import BaseSearchRequest, ImageSearchRequest, TextSearchRequest

class KeyframeQueryService:
    def __init__(
            self, 
            keyframe_vector_repo: KeyframeVectorRepository,
            keyframe_mongo_repo: KeyframeRepository,
            
        ):

        self.keyframe_vector_repo = keyframe_vector_repo
        self.keyframe_mongo_repo= keyframe_mongo_repo
        self.data_folder = ''

    def convert_model_to_path(
            self,
            model: KeyframeInterface
        ) -> tuple[int, str]:
            return model.key, os.path.join(self.data_folder, f'Keyframes_L{model.group_num:02d}', f'L{model.group_num:02d}_V{model.video_num:03d}', f'{model.keyframe_num:03d}.jpg')
    
    async def _retrieve_keyframes(self, ids: list[int]):
        keyframes = await self.keyframe_mongo_repo.get_keyframe_by_list_of_keys(ids)
        print(keyframes[:5])
        keyframe_map = {k.key: k for k in keyframes}
        return_keyframe = [
            keyframe_map[k] for k in ids
        ]   
        return return_keyframe
    
    async def _search_keyframes(
        self,
        text_embedding: list[float],
        top_k: int,
    ):
        
        search_request = MilvusSearchRequest(
            embedding=text_embedding,
            top_k=top_k,
        )

        search_response = await self.keyframe_vector_repo.search_by_embedding(search_request)

        sorted_results = sorted(
            search_response.results, key=lambda r: r.distance, reverse=True
        )
        ids = []
        dists = []
        for result in sorted_results:
            ids.append(result.id_)
            dists.append(result.distance)
        return ids, dists
    

    async def search_by_text(
        self,
        text_embedding: list[float],
        search_request: TextSearchRequest
    ):
        top_n = search_request.oversample * search_request.size * search_request.page
        ids, dists = await self._search_keyframes(text_embedding, top_n)   
        pairs = list(zip(ids, dists))
        ids = await self.keyframe_mongo_repo.filter_by_objects(ids, search_request.obj_filters)
        pairs = [(id_, dist) for (id_, dist) in pairs if id_ in ids]
        ranked_ids = [id for (id, _) in pairs]
        start, end = (search_request.page - 1) * search_request.size, search_request.page * search_request.size
        keyframes = await self._retrieve_keyframes(ranked_ids[start:end])
        response = []
        for kf in keyframes:
            id, path = self.convert_model_to_path(kf)
            response.append(
                    KeyframeServiceReponse(
                        id=id,
                        path=path)                        
                )
        return response
        
    async def get_frames_by_page(self, search_request: BaseSearchRequest) -> list[KeyframeServiceReponse]:
        results = await self.keyframe_mongo_repo.get_frames_by_page(search_request)
        return list(map(lambda pair: KeyframeServiceReponse(id=pair[0], path=pair[1]), map(self.convert_model_to_path, results)))

    async def image_search(self, search_request: ImageSearchRequest) -> list[KeyframeServiceReponse]:
        search_results = await self.keyframe_vector_repo.search_by_img_id(search_request)
        
        sorted_results = sorted(
            search_results.results, key=lambda r: r.distance, reverse=True
        )

        sorted_ids = [result.id_ for result in sorted_results]

        keyframes = await self._retrieve_keyframes(sorted_ids)

        keyframe_map = {k.key: k for k in keyframes}
        response = []

        for result in sorted_results:
            keyframe = keyframe_map.get(result.id_) 
            if keyframe is not None:
                id, path = self.convert_model_to_path(KeyframeInterface(
                    key=keyframe.key,
                    video_num=keyframe.video_num,
                    group_num=keyframe.group_num,
                    keyframe_num=keyframe.keyframe_num,
                ))
                response.append(
                    KeyframeServiceReponse(
                        id=id,
                        path=path)                        
                )
        return response
