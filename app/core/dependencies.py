
from pathlib import Path
from fastapi import Depends, Request, HTTPException
from functools import lru_cache
import json

import os
import sys
ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '../'
    )
)

sys.path.insert(0, ROOT_DIR)


from controller.query_controller import QueryController
from service import ModelService, KeyframeQueryService, TranslationService
from core.settings import KeyFrameIndexMilvusSetting, MongoDBSettings, AppSettings
from factory.factory import ServiceFactory
from core.logger import SimpleLogger

from llama_index.llms.google_genai import GoogleGenAI
from controller.agent_controller import AgentController
from llama_index.core.llms import LLM

logger = SimpleLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

@lru_cache
def get_llm() -> LLM:
    return GoogleGenAI(
        'gemini-2.5-flash-lite',
        api_key=os.getenv('GOOGLE_GENAI_API')
    )

@lru_cache()
def get_app_settings():
    """Get MongoDB settings (cached)"""
    return AppSettings()

@lru_cache()
def get_milvus_settings():
    """Get Milvus settings (cached)"""
    return KeyFrameIndexMilvusSetting()

@lru_cache()
def get_mongo_settings():
    """Get MongoDB settings (cached)"""
    return MongoDBSettings()

def get_service_factory(request: Request) -> ServiceFactory:
    """Get ServiceFactory from app state"""
    service_factory = getattr(request.app.state, 'service_factory', None)
    if service_factory is None:
        logger.error("ServiceFactory not found in app state")
        raise HTTPException(
            status_code=503, 
            detail="Service factory not initialized. Please check application startup."
        )
    return service_factory

def get_agent_controller(
    service_factory = Depends(get_service_factory),
    app_settings: AppSettings = Depends(get_app_settings)
) -> AgentController:
    llm = get_llm()
    keyframe_service = service_factory.get_keyframe_query_service()
    model_service = service_factory.get_model_service()

    data_folder = app_settings.DATA_FOLDER
    objects_data_path = Path(app_settings.FRAME2OBJECT)
    asr_data_path = Path(app_settings.ASR_PATH)

    return AgentController(
        llm=llm,
        keyframe_service=keyframe_service,
        model_service=model_service,
        data_folder=data_folder,
        objects_data_path=objects_data_path,
        asr_data_path=asr_data_path,
        top_k=50
    )

def get_model_service(service_factory: ServiceFactory = Depends(get_service_factory)) -> ModelService:
    try:
        model_service = service_factory.get_model_service()
        if model_service is None:
            logger.error("Model service not available from factory")
            raise HTTPException(
                status_code=503,
                detail="Model service not available"
            )
        return model_service
    except Exception as e:
        logger.error(f"Failed to get model service: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Model service initialization failed: {str(e)}"
        )
    
def get_keyframe_service(service_factory: ServiceFactory = Depends(get_service_factory)) -> KeyframeQueryService:
    """Get keyframe query service from ServiceFactory"""
    try:
        keyframe_service = service_factory.get_keyframe_query_service()
        if keyframe_service is None:
            logger.error("Keyframe service not available from factory")
            raise HTTPException(
                status_code=503,
                detail="Keyframe service not available"
            )
        return keyframe_service
    except Exception as e:
        logger.error(f"Failed to get keyframe service: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Keyframe service initialization failed: {str(e)}"
        )

def get_translate_service(service_factory: ServiceFactory = Depends(get_service_factory)) -> TranslationService:
    try:
        translate_service = service_factory.get_translate_service()
        if translate_service is None:
            logger.error("Translate service not available from factory")
            raise HTTPException(
                status_code=503,
                detail="Translate service not available"
            )
        return translate_service
    except Exception as e:
        logger.error(f"Failed to get translate service: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Translate service initialization failed: {str(e)}"
        )

def get_mongo_client(request: Request):
    """Get MongoDB client from app state"""
    mongo_client = getattr(request.app.state, 'mongo_client', None)
    if mongo_client is None:
        logger.error("MongoDB client not found in app state")
        raise HTTPException(
            status_code=503,
            detail="MongoDB client not initialized"
        )
    return mongo_client

async def check_mongodb_health(request: Request) -> bool:
    """Check MongoDB connection health"""
    try:
        mongo_client = get_mongo_client(request)
        await mongo_client.admin.command('ping')
        return True
    except Exception as e:
        logger.error(f"MongoDB health check failed: {str(e)}")
        return False


def get_milvus_repository(service_factory: ServiceFactory = Depends(get_service_factory)):
    """Get Milvus repository from ServiceFactory"""
    try:
        repository = service_factory.get_milvus_keyframe_repo()
        if repository is None:
            raise HTTPException(
                status_code=503,
                detail="Milvus repository not available"
            )
        return repository
    except Exception as e:
        logger.error(f"Failed to get Milvus repository: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Milvus repository initialization failed: {str(e)}"
        )


def get_query_controller(
    model_service: ModelService = Depends(get_model_service),
    keyframe_service: KeyframeQueryService = Depends(get_keyframe_service),
    translate_service: TranslationService = Depends(get_translate_service),
    app_settings: AppSettings = Depends(get_app_settings)
) -> QueryController:
    """Get query controller instance"""
    try:
        logger.info("Creating query controller...")
        
        object_classes_path = Path(app_settings.OBJECT_CLASSES_PATH)
        
        controller = QueryController(
            object_classes_path=object_classes_path,
            model_service=model_service,
            keyframe_service=keyframe_service,
            translate_service=translate_service,
        )
        
        logger.info("Query controller created successfully")
        return controller
        
    except Exception as e:
        logger.error(f"Failed to create query controller: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Query controller initialization failed: {str(e)}"
        )