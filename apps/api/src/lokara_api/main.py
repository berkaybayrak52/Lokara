"""FastAPI app factory. Serve with `uv run lokara-api` (or uvicorn directly)."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    auth,
    buildings,
    costs,
    demo,
    extraction,
    health,
    me,
    meters,
    portal,
    statements,
)
from .settings import ApiSettings


def create_app() -> FastAPI:
    settings = ApiSettings()
    app = FastAPI(title="Lokara API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(demo.router)
    app.include_router(portal.router)
    app.include_router(buildings.router)
    app.include_router(costs.router)
    app.include_router(meters.router)
    app.include_router(extraction.router)
    app.include_router(statements.router)
    return app


app = create_app()


def run() -> None:
    uvicorn.run("lokara_api.main:app", host="127.0.0.1", port=ApiSettings().api_port)
