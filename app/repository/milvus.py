"""
The implementation of Vector Repository. The following class is responsible for getting the vector by many ways
Including Faiss and Usearch
"""


import os
import sys
ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '../'
    )
)
sys.path.insert(0, ROOT_DIR)

from typing import cast, Optional, List, Tuple
from common.repository import MilvusBaseRepository
from pymilvus import Collection as MilvusCollection
from pymilvus.client.search_result import SearchResult
from schema.interface import  MilvusSearchRequest, MilvusSearchResult, MilvusSearchResponse
from schema.request import ImageSearchRequest

class KeyframeVectorRepository(MilvusBaseRepository):
    def __init__(
        self, 
        collection: MilvusCollection,
        search_params: dict
    ):
        super().__init__(collection)
        self.search_params = search_params
    
    async def search_by_embedding(
        self,
        request: MilvusSearchRequest
    ):
        expr = None
        if request.exclude_ids:
            expr = f"id not in {request.exclude_ids}"
        
        search_results= cast(SearchResult, self.collection.search(
            data=[request.embedding],
            anns_field="embedding",
            param=self.search_params,
            limit=request.top_k,
            expr=expr ,
            output_fields=["id"],
            _async=False
        ))


        results = []
        for hits in search_results:
            for hit in hits:
                result = MilvusSearchResult(
                    id_=hit.id,
                    distance=hit.distance,
                )
                results.append(result)
        
        return MilvusSearchResponse(
            results=results,
            total_found=len(results),
        )
    
    def get_total(self):
        return self.collection.num_entities
    
    async def search_by_img_id(
        self,
        search_request: ImageSearchRequest,
        exclude_ids: Optional[list[int]] = None,
    ):
        """
        Tìm hàng xóm của ảnh có id = imgid bằng chính embedding của nó.
        - page: bắt đầu từ 0
        - size: số lượng kết quả mỗi trang
        Trả về list [neighbor_id] sắp xếp theo score giảm dần.
        """

        # 1) Lấy embedding của imgid
        q = self.collection.query(
            expr=f"id == {search_request.imgid}",
            output_fields=["embedding"]
        )
        if not q:
            return []

        query_emb = q[0]["embedding"]

        # 2) Xây expr loại chính nó + các id cần exclude (nếu có)
        excludes = set(exclude_ids or [])
        excludes.add(search_request.imgid)
        expr_parts = []
        if excludes:
            expr_parts.append(f"id not in {list(excludes)}")
        expr = " and ".join(expr_parts) if expr_parts else None

        skip = (search_request.page - 1) * search_request.size
        self.search_params['offset'] = skip
        
        search_res = self.collection.search(
            data=[query_emb],
            anns_field="embedding",
            param=self.search_params,  
            limit=search_request.size,
            expr=expr,
            output_fields=["id"],        # không cần lấy embedding khi duyệt hàng xóm
            _async=False
        )

        results = []
        for hits in search_res:
            for hit in hits:
                result = MilvusSearchResult(
                    id_=hit.id,
                    distance=hit.distance,
                )
                results.append(result)
        return MilvusSearchResponse(
            results=results,
            total_found=len(results),
        )
