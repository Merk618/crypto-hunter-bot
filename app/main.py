"""FastAPI entrypoint for Crypto Hunter."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.storage.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize SQLite journal tables when enabled."""
    if get_settings().enable_trade_journal:
        init_db()
    yield


app = FastAPI(title="Crypto Hunter Bot", version="0.1.0", lifespan=lifespan)
app.include_router(router)
