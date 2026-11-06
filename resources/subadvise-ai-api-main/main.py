from contextlib import asynccontextmanager
import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controller.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key is None or not groq_api_key.strip():
        raise RuntimeError(
            "GROQ_API_KEY must be set before starting the SubAdvise AI API."
        )

    base_url = os.getenv(
        "SUBADVISE_API_BASE_URL",
        "http://localhost:7071",
    ).rstrip("/")
    app.state.groq_api_key = groq_api_key.strip()
    app.state.groq_api_key_lock = asyncio.Lock()
    app.state.pending_changes = {}
    app.state.pending_changes_lock = asyncio.Lock()
    app.state.subadvise_client = httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(15.0),
    )
    project_dir = Path(__file__).resolve().parent
    history_dir = Path(
        os.getenv("CHAT_HISTORY_DIR", str(project_dir / "data" / "chat_history"))
    )
    vector_dir = Path(
        os.getenv("CHAT_VECTOR_DIR", str(project_dir / "data" / "chroma_db"))
    )
    try:
        from memory_manager import HybridChatMemory

        app.state.chat_memory = HybridChatMemory.from_paths(history_dir, vector_dir)
    except (OSError, RuntimeError):
        await app.state.subadvise_client.aclose()
        raise
    try:
        yield
    finally:
        await app.state.subadvise_client.aclose()


app = FastAPI(
    title="SubAdvise AI API",
    description=(
        "FastAPI proxy and Groq assistant with persistent hybrid chat memory."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:7071",
        "http://localhost:7073",
        "http://127.0.0.1:7071",
        "http://127.0.0.1:7073",
    ],
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)
