from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import datetime
import random

from app.database import get_db
from app.models import Video, AgentLog
from app.queue_worker import enqueue, VideoTask, task_queue

router = APIRouter(prefix="/api/videos", tags=["videos"])


class CreateVideoRequest(BaseModel):
    video_title: str
    channel_id: str = "default"
    niche: str = "finance"
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"
    character_style: str = "family_guy"
    target_duration: int = 120


@router.post("")
async def create_video(req: CreateVideoRequest, db: AsyncSession = Depends(get_db)):
    video_id = f"vid_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{random.randint(1000,9999)}"
    video = Video(video_id=video_id, video_title=req.video_title,
                  channel_id=req.channel_id, status="pending")
    db.add(video)
    await db.commit()

    task = VideoTask(
        video_id=video_id, video_title=req.video_title, channel_id=req.channel_id,
        niche=req.niche, voice_id=req.voice_id,
        character_style=req.character_style, target_duration=req.target_duration,
    )
    await enqueue(task)
    return {"video_id": video_id, "status": "pending", "queue_size": task_queue.qsize()}


@router.get("")
async def list_videos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).order_by(desc(Video.created_at)).limit(50))
    videos = result.scalars().all()
    return [{"id": v.id, "video_id": v.video_id, "video_title": v.video_title,
             "channel_id": v.channel_id, "status": v.status,
             "scene_count": v.scene_count, "total_duration": v.total_duration,
             "final_video_url": v.final_video_url, "error_message": v.error_message,
             "created_at": v.created_at.isoformat() if v.created_at else None,
             "completed_at": v.completed_at.isoformat() if v.completed_at else None}
            for v in videos]


@router.get("/{video_id}")
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.video_id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Video not found")
    return {"video_id": video.video_id, "video_title": video.video_title,
            "status": video.status, "scene_count": video.scene_count,
            "total_duration": video.total_duration, "final_video_url": video.final_video_url,
            "error_message": video.error_message,
            "created_at": video.created_at.isoformat() if video.created_at else None}


@router.get("/{video_id}/logs")
async def get_video_logs(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentLog).where(AgentLog.video_id == video_id).order_by(AgentLog.timestamp))
    logs = result.scalars().all()
    return [{"agent": l.agent, "message": l.message, "level": l.level,
             "timestamp": l.timestamp.isoformat()} for l in logs]
