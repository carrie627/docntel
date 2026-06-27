from fastapi import FastAPI, status, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Annotated
from .api.router import api_router
from .services.vector_db import init_vector_db
from .core.config import get_settings, Settings
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):

    # startup
    await init_vector_db()

    yield

    # shutdown
    print("Shutting down...")


app = FastAPI(
    lifespan=lifespan
)


origins = [
    "http://localhost:3000",  # Default Next.js local port
    # "https://yourdomain.com", # Add production domain here later
]

# 2. Add the CORS middleware to your app instance
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Allows your frontend to connect
    allow_credentials=True,      # Required because your fetch has credentials: "include"
    allow_methods=["*"],         # Allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],         # Allows all headers
)


# keep sensetive docs away from this. but for development and testing it is ok.
Path("storage/uploads").mkdir(parents=True, exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(directory="storage/uploads"),
    name="uploads"
)

app.include_router(api_router, prefix="/api")


@app.get("/info")
async def info(settings: Annotated[Settings, Depends(get_settings)]):
    return {
        "app_name": settings.app_name,
        "database_url": settings.database_url
    }


@app.get("/")
async def root():
    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "success": True,
        "status_code": status.HTTP_200_OK,
        "message": "Homepage content loaded",
        "data": {
            "header": "Welcome to DOCNTEL",
            "sub_header": "Your private AI Customer Support Agent for your Store",
            "demo_btn_msg": "Try a demo",
            "chat_btn_msg": "Chat"
        },
    })
