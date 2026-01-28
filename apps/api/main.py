from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from db.neo4j import close_neo4j, init_neo4j
from db.postgres import close_postgres, init_postgres
from db.redis import close_redis, init_redis
from routers import capture, dashboard, decisions, entities, graph, ingest, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_postgres()
    await init_neo4j()
    await init_redis()
    yield
    # Shutdown
    await close_postgres()
    await close_neo4j()
    await close_redis()


app = FastAPI(
    title="Continuum API",
    description="Knowledge Management Platform API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(decisions.router, prefix="/api/decisions", tags=["Decisions"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(capture.router, prefix="/api/capture", tags=["Capture"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingest"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(entities.router, prefix="/api/entities", tags=["Entities"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/")
async def root():
    return {
        "name": "Continuum API",
        "version": "0.1.0",
        "docs": "/docs",
    }
