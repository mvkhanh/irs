from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


from router import keyframe_api, agent_api
from core.lifespan import lifespan
from core.logger import SimpleLogger

logger = SimpleLogger(__name__)


app = FastAPI(
    title="Keyframe Search API",
    description="""
    ## Keyframe Search API

    A powerful semantic search API for video keyframes using vector embeddings.

    ### Features

    ### Getting Started

    Try the simple search endpoint `/keyframe/` with a natural language query
    like "person walking in park" or "sunset over mountains".
    """,
    version="1.0.0",
    contact={
        "name": "Keyframe Search Team",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan
)

#
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')

app.include_router(keyframe_api.router)
app.include_router(agent_api.router)

@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Keyframe Search API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/keyframe/health",
        "search": "/keyframe/"
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  
        log_level="info"
    )