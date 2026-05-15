"""FastAPI entrypoint for Crypto Hunter."""

from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Crypto Hunter Bot", version="0.1.0")
app.include_router(router)
