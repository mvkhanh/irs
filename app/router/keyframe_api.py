
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.encoders import jsonable_encoder
from pathlib import Path
from typing import Annotated

from schema.request import (
    ImageSearchRequest,
    UnifiedSearchRequest
)
from controller.query_controller import QueryController
from core.dependencies import get_query_controller
from core.logger import SimpleLogger


logger = SimpleLogger(__name__)
router = APIRouter(
    prefix="/keyframe",
    tags=["keyframe"],
    responses={404: {"description": "Not found"}},
)

from core.view import templates

PLACEHOLDER = Path(__file__).resolve().parents[1] / "static/images/404.jpg"

@router.get('/get_img')
async def get_img(fpath: str):
    p = Path(fpath)
    if not p.is_file():
        p = PLACEHOLDER
    
    return FileResponse(p, media_type="image/jpeg")

@router.get('/neighbors')
async def get_neighbors(imgid: int, k: int = 10, controller: QueryController = Depends(get_query_controller)):
    results = await controller.get_neighbors(imgid, k)
    return jsonable_encoder(results)

@router.get('/imgsearch', response_class=HTMLResponse)
async def image_search(request: Request, search_request: Annotated[ImageSearchRequest, Depends()], controller: QueryController = Depends(get_query_controller)):
    results = await controller.image_search(search_request)
    return templates.TemplateResponse(request=request, name='home.html', context={'data': jsonable_encoder(results)})
  
@router.get('/objects')
async def get_objects_list(controller: QueryController = Depends(get_query_controller)):
    with open(controller.object_classes_path, 'r') as f:
        obj_classes = [x for x in f.read().split('\n') if x.strip()]
    return {'classes': obj_classes}

@router.get('/', response_class=HTMLResponse, name='keyframe_unified_search_page')
async def unified_search_page(
    request: Request,
    search_request: Annotated[UnifiedSearchRequest, Depends()],
    controller: QueryController = Depends(get_query_controller),
):
    results = await controller.unified_search(search_request)
    return templates.TemplateResponse(request=request, name='home.html', context={'data': jsonable_encoder(results)})

@router.post('/search', name='keyframe_unified_search_api')
async def unified_search_api(
    search_request: UnifiedSearchRequest,  # POST body JSON
    controller: QueryController = Depends(get_query_controller),
):
    results = await controller.unified_search(search_request)
    return jsonable_encoder(results)