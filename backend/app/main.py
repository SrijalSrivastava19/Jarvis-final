"""
Jarvis backend entrypoint.

Wires together config, logging, database init, routers, CORS, and global
exception handlers. Run with: uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_chat,
    routes_health,
    routes_voice,
    routes_news,
    routes_weather,
)
from app.config import settings
from app.core.exceptions import JarvisError, jarvis_error_handler, unhandled_exception_handler
from app.db.database import init_db
from app.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Jarvis backend (env=%s)...", settings.app_env)
    await init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Shutting down Jarvis backend.")


app = FastAPI(
    title="Jarvis AI Assistant API",
    description="Jarvis AI Assistant (Voice, News, Weather)",
    version="0.3.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(JarvisError, jarvis_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(routes_health.router)
app.include_router(routes_chat.router)
app.include_router(routes_voice.router)
app.include_router(routes_news.router)
app.include_router(routes_weather.router)

@app.get("/")
async def root():
    return {
        "name": "Jarvis AI Assistant API",
        "version": "0.3.0",
        "modules": [
            "Voice",
            "News",
            "Weather"
        ],
        "docs": "/docs"
    }