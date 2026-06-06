from contextlib import asynccontextmanager
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.api.routes.auth import router as auth_router
from app.api.routes.contracts import router as contracts_router
from app.api.routes.health import router as health_router
from app.api.routes.review_logs import router as review_logs_router
from app.api.routes.review_rules import router as review_rules_router
from app.api.routes.review_versions import router as review_versions_router
from app.api.routes.system_settings import router as system_settings_router
from app.api.routes.users import router as users_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.contract_service import ensure_upload_dir
from app.services.user_service import ensure_default_admin


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_upload_dir()
    db: Session = SessionLocal()
    try:
        ensure_default_admin(db)
    except (OperationalError, ProgrammingError):
        db.rollback()
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"服务器内部错误：{type(exc).__name__}: {exc}"},
    )

cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(contracts_router)
app.include_router(users_router)
app.include_router(review_rules_router)
app.include_router(review_versions_router)
app.include_router(review_logs_router)
app.include_router(system_settings_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Backend is running"}
