from __future__ import annotations
from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.errors import NotFoundError, ConflictError


from app.api.rest import router as rest_router
from app.api.graphql import build_graphql_router
from app.db.init_db import init_db
from app.core.exception_handlers import register_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Multi-Tenant Reconciliation API (MVP)")

    register_exception_handlers(app)


    init_db()

    app.include_router(rest_router)

    app.include_router(build_graphql_router(), prefix="/graphql")
    return app

app = create_app()

