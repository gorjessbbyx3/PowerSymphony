"""Application bootstrap helpers for the FastAPI server."""

import os
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from server import state
from server.config_schema_router import router as config_schema_router
from server.routes import ALL_ROUTERS
from utils.error_handler import add_exception_handlers
from utils.middleware import add_middleware

logger = logging.getLogger(__name__)


def init_app(app: FastAPI) -> None:
    """Apply shared middleware, routers, and global state to ``app``."""

    add_exception_handlers(app)
    add_middleware(app)

    state.init_state()

    try:
        from server.services.db import init_schema
        init_schema()
        logger.info("Database schema initialized")
    except Exception as e:
        logger.warning(f"Database schema init skipped: {e}")

    for router in ALL_ROUTERS:
        app.include_router(router)

    app.include_router(config_schema_router)

    dist_dir = Path("frontend/dist")
    if dist_dir.is_dir():
        from fastapi.responses import FileResponse

        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="static-assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            file_path = dist_dir / full_path
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(dist_dir / "index.html"))
