from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_app_config
from app.db.init_db import init_db

config = get_app_config()

app = FastAPI(title=config.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# Ensure the schema exists even when the app is instantiated in test helpers that do not
# enter a startup lifecycle context first.
init_db()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/")
def root() -> dict:
    return {"service": config.app_name, "status": "online"}
