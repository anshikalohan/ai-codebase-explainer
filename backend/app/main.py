"""
AI Codebase Explainer - FastAPI Backend
Production-ready RAG system for codebase understanding
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.vector_store import vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Starting AI Codebase Explainer...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    yield
    logger.info("🛑 Shutting down AI Codebase Explainer...")
    vector_store.clear()


app = FastAPI(
    title="AI Codebase Explainer",
    description="RAG-powered codebase understanding API",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins to fix frontend connectivity
    allow_credentials=False, # Must be False when origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }
