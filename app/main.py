from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import asyncio
import os
import logging

from app.database import init_db
from app.routers import videos, channels, settings, dashboard
from app.queue_worker import worker_loop, recover_stuck_jobs, keep_alive_loop
from app.telegram_bot import polling_loop, router as telegram_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await recover_stuck_jobs()
    asyncio.create_task(worker_loop())
    asyncio.create_task(keep_alive_loop())
    asyncio.create_task(polling_loop())
    yield


app = FastAPI(title="Video Automation Dashboard", lifespan=lifespan)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})

app.include_router(videos.router)
app.include_router(channels.router)
app.include_router(settings.router)
app.include_router(dashboard.router)
app.include_router(telegram_router)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))
