"""
Persistent task queue worker.
- Uses asyncio.Queue as in-memory queue
- On startup, re-queues any 'pending' or stuck 'in-progress' jobs from DB
- Worker loop runs forever inside the app lifespan
- Keep-alive pings /health every 4 minutes to prevent HF Spaces sleep
"""
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Video

log = logging.getLogger("queue_worker")

# Global in-memory queue
task_queue: asyncio.Queue = asyncio.Queue()

IN_PROGRESS_STATUSES = {
    "generating_script", "script_ready",
    "generating_chunks", "compiling",
}


@dataclass
class VideoTask:
    video_id: str
    video_title: str
    channel_id: str
    niche: str
    voice_id: str
    character_style: str
    target_duration: int


async def enqueue(task: VideoTask):
    await task_queue.put(task)
    log.info(f"Enqueued task: {task.video_id}")


async def _run_task(task: VideoTask):
    from app.agents.orchestrator import run_pipeline
    async with AsyncSessionLocal() as db:
        try:
            await run_pipeline(
                db, task.video_id, task.video_title, task.channel_id,
                task.niche, task.voice_id, task.character_style, task.target_duration,
            )
        except Exception as e:
            log.error(f"Task {task.video_id} failed: {e}")


async def worker_loop():
    """Runs forever, processes tasks one by one."""
    log.info("Queue worker started")
    while True:
        try:
            task: VideoTask = await task_queue.get()
            log.info(f"Processing task: {task.video_id}")
            await _run_task(task)
            task_queue.task_done()
        except Exception as e:
            log.error(f"Worker loop error: {e}")
            await asyncio.sleep(2)


async def recover_stuck_jobs():
    """On startup: re-queue pending/stuck jobs from DB."""
    async with AsyncSessionLocal() as db:
        stuck_cutoff = datetime.utcnow() - timedelta(hours=2)
        result = await db.execute(
            select(Video).where(
                Video.status.in_(["pending"] + list(IN_PROGRESS_STATUSES)),
                Video.created_at > stuck_cutoff,
            )
        )
        videos = result.scalars().all()
        for v in videos:
            task = VideoTask(
                video_id=v.video_id,
                video_title=v.video_title,
                channel_id=v.channel_id,
                niche="finance",        # defaults – channel config loaded inside orchestrator
                voice_id="EXAVITQu4vr4xnSDxMaL",
                character_style="family_guy",
                target_duration=120,
            )
            await task_queue.put(task)
            log.info(f"Recovered stuck job: {v.video_id} (was: {v.status})")


async def keep_alive_loop():
    """Pings /health every 4 minutes to prevent HF Spaces from sleeping."""
    port = os.getenv("PORT", "7860")
    url = f"http://localhost:{port}/health"
    await asyncio.sleep(30)  # wait for app to fully start
    while True:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url)
                log.debug(f"Keep-alive ping: {r.status_code}")
        except Exception as e:
            log.warning(f"Keep-alive failed: {e}")
        await asyncio.sleep(240)  # 4 minutes
