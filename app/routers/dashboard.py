from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import get_db
from app.models import Video, ErrorLog, AgentLog
from app.queue_worker import task_queue

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(Video))).scalar()
    completed = (await db.execute(
        select(func.count()).select_from(Video).where(Video.status == "completed"))).scalar()
    failed = (await db.execute(
        select(func.count()).select_from(Video).where(Video.status == "failed"))).scalar()
    in_progress = (await db.execute(
        select(func.count()).select_from(Video).where(
            Video.status.notin_(["completed", "failed", "pending"])))).scalar()
    errors = (await db.execute(select(func.count()).select_from(ErrorLog))).scalar()

    return {
        "total_videos": total, "completed": completed, "failed": failed,
        "in_progress": in_progress, "total_errors": errors,
        "queue_size": task_queue.qsize(),
    }


@router.get("/recent-errors")
async def recent_errors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ErrorLog).order_by(desc(ErrorLog.timestamp)).limit(20))
    logs = result.scalars().all()
    return [{"id": l.id, "workflow": l.workflow, "node_name": l.node_name,
             "error_message": l.error_message, "video_id": l.video_id,
             "timestamp": l.timestamp.isoformat()} for l in logs]
