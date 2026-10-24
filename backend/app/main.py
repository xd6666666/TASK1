from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import Base, engine
from app.seed import seed

settings = get_settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
if settings.database_url.startswith("sqlite"):
    Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"code": 500, "msg": str(exc), "data": None})


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed()


@app.get("/api/health")
def health():
    db_kind = "mysql" if settings.database_url.startswith("mysql") else "sqlite"
    vector_kind = (
        "milvus"
        if settings.vector_uri.startswith("http://") or settings.vector_uri.startswith("https://")
        else "milvus-lite"
    )
    return {
        "code": 200,
        "msg": "ok",
        "data": {
            "app": settings.app_name,
            "llm_mock": settings.llm_mock,
            "database": db_kind,
            "vector": vector_kind,
            "vector_uri": settings.vector_uri,
        },
    }
