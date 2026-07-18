import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import admin, auth, credit, dashboard, lender, sme, transactions
from app.services.ml_predictor import get_predictor, reload_predictor
from app.services.ml_training import train_models

logger = logging.getLogger(__name__)


def init_db() -> None:
    settings = get_settings()
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    os.makedirs(settings.model_dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    from app.schema_migrate import migrate_schema

    migrate_schema()


def ensure_model() -> None:
    settings = get_settings()
    meta_path = Path(settings.model_dir) / "model_meta.json"
    if not meta_path.exists():
        logger.info("No trained model found – training on startup...")
        db = SessionLocal()
        try:
            train_models(db_session=db)
        finally:
            db.close()
        reload_predictor()
    else:
        get_predictor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_model()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Supply-chain credit risk API for SME and Lender roles",
        lifespan=lifespan,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    api_prefix = "/api"
    application.include_router(admin.router, prefix=api_prefix)
    application.include_router(auth.router, prefix=api_prefix)
    application.include_router(sme.router, prefix=api_prefix)
    application.include_router(transactions.router, prefix=api_prefix)
    application.include_router(credit.router, prefix=api_prefix)
    application.include_router(lender.router, prefix=api_prefix)
    application.include_router(dashboard.router, prefix=api_prefix)

    return application


app = create_app()
