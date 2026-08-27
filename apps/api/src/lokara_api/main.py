"""FastAPI app factory. Serve with `uv run lokara-api` (or uvicorn directly)."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    advances,
    auth,
    buildings,
    costs,
    demo,
    extraction,
    finalized_statements,
    guards_delivery,
    health,
    mdl,
    me,
    meters,
    payments,
    portal,
    statement_drafts,
    statements,
    tax,
    uvi_runs,
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
    app.include_router(advances.router)
    app.include_router(finalized_statements.router)
    app.include_router(finalized_statements.root_router)
    # FastAPI 0.139 keeps ``include_router`` branches lazy. M9's authorization
    # contract audits each concrete APIRoute and its dependency graph, so keep
    # this bounded router materialized in the application route table.
    app.router.routes.extend(guards_delivery.router.routes)
    app.include_router(buildings.router)
    app.include_router(costs.router)
    app.include_router(meters.router)
    app.include_router(mdl.router)
    app.include_router(extraction.router)
    app.include_router(statements.router)
    app.include_router(statement_drafts.router)
    app.include_router(payments.router)
    app.include_router(uvi_runs.router)
    app.include_router(tax.router)
    return app


app = create_app()


def run() -> None:
    uvicorn.run("lokara_api.main:app", host="127.0.0.1", port=ApiSettings().api_port)
