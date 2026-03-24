"""Base agent with logging and DB access."""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AgentLog, ErrorLog


class BaseAgent:
    def __init__(self, db: AsyncSession, video_id: str):
        self.db = db
        self.video_id = video_id

    async def log(self, message: str, level: str = "info", agent: str = ""):
        entry = AgentLog(
            video_id=self.video_id,
            agent=agent or self.__class__.__name__,
            message=message,
            level=level,
            timestamp=datetime.utcnow(),
        )
        self.db.add(entry)
        await self.db.commit()

    async def log_error(self, workflow: str, node: str, message: str, scene_id: str = None):
        entry = ErrorLog(
            workflow=workflow,
            node_name=node,
            error_message=message,
            video_id=self.video_id,
            scene_id=scene_id,
            timestamp=datetime.utcnow(),
        )
        self.db.add(entry)
        await self.db.commit()
