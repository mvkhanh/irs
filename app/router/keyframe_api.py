
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.encoders import jsonable_encoder
from pathlib import Path
from typing import Annotated


from schema.request import (
    BaseSearchRequest,
    TextSearchRequest,
    ImageSearchRequest
)
from schema.response import KeyframeServiceReponse, KeyframeDisplay
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

@router.get('/', response_class=HTMLResponse)
async def get_index(request: Request, search_request: Annotated[BaseSearchRequest, Depends()], controller: QueryController = Depends(get_query_controller)):
    results = await controller.get_frames_by_page(search_request)
    return templates.TemplateResponse(request=request, name='home.html', context={'data': jsonable_encoder(results)})

@router.get('/get_img')
async def get_img(fpath: str):
    p = Path(fpath)
    if not p.is_file():
        p = PLACEHOLDER
    
    return FileResponse(p, media_type="image/jpeg")

@router.get('/neighbors')
async def get_neighbors(imgid: str, k: int = 10, controller: QueryController = Depends(get_query_controller)):
    return await controller.get_neighbors(imgid, k)

@router.get('/imgsearch', response_class=HTMLResponse)
async def image_search(request: Request, search_request: Annotated[ImageSearchRequest, Depends()], controller: QueryController = Depends(get_query_controller)):
    results = await controller.image_search(search_request)
    return templates.TemplateResponse(request=request, name='home.html', context={'data': jsonable_encoder(results)})

@router.get('/textsearch', response_class=HTMLResponse)
async def text_search(request: Request, search_request: Annotated[TextSearchRequest, Depends()], controller: QueryController = Depends(get_query_controller)):
    results = await controller.text_search(search_request)
    return templates.TemplateResponse(request=request, name='home.html', context={'data': jsonable_encoder(results)})
    
@router.get('/objects')
async def get_objects_list(controller: QueryController = Depends(get_query_controller)):
    with open(controller.object_classes_path, 'r') as f:
        obj_classes = [x for x in f.read().split('\n') if x.strip()]
    return {'classes': obj_classes}

