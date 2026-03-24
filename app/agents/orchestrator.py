"""Main pipeline orchestrator – coordinates all agents."""
import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Video
from app.agents.script_agent import ScriptAgent
from app.agents.audio_agent import AudioAgent
from app.agents.image_agent import ImageAgent
from app.agents.video_agent import VideoAgent
from app.agents.storage_agent import StorageAgent
from app.agents.base import BaseAgent


async def _update_video_status(db: AsyncSession, video_id: str, status: str, **kwargs):
    result = await db.execute(select(Video).where(Video.video_id == video_id))
    video = result.scalar_one_or_none()
    if video:
        video.status = status
        for k, v in kwargs.items():
            setattr(video, k, v)
        await db.commit()


async def run_pipeline(db: AsyncSession, video_id: str, title: str, channel_id: str,
                       niche: str, voice_id: str, character_style: str, duration: int):
    """Full video generation pipeline."""
    base = BaseAgent(db, video_id)

    try:
        # ── WF-002: Script Generation ──────────────────────────────────────
        await _update_video_status(db, video_id, "generating_script")
        script_agent = ScriptAgent(db, video_id)
        script = await script_agent.generate(title, niche, duration)
        await _update_video_status(db, video_id, "script_ready",
                                   script_json=json.dumps(script),
                                   scene_count=len(script["scenes"]))

        # ── WF-003/004: Per-scene chunk generation ─────────────────────────
        await _update_video_status(db, video_id, "generating_chunks")
        chunk_results = []
        semaphore = asyncio.Semaphore(3)  # max 3 concurrent scenes

        async def process_scene(scene: dict):
            async with semaphore:
                return await _process_scene(db, video_id, scene, voice_id)

        tasks = [process_scene(s) for s in script["scenes"]]
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out errors
        valid_chunks = [c for c in chunk_results if isinstance(c, dict) and c.get("clip_url")]
        if not valid_chunks:
            raise RuntimeError("All scene chunks failed to generate")

        valid_chunks.sort(key=lambda c: c.get("scene_id", 0))
        clip_urls = [c["clip_url"] for c in valid_chunks]

        # ── WF-006: Final Compilation ──────────────────────────────────────
        await _update_video_status(db, video_id, "compiling")
        video_agent = VideoAgent(db, video_id)
        final_url = await video_agent.concatenate_clips(clip_urls)

        total_duration = sum(c.get("duration", 0) for c in valid_chunks)
        await _update_video_status(
            db, video_id, "completed",
            final_video_url=final_url,
            total_duration=total_duration,
            total_scenes=len(valid_chunks),
            completed_at=datetime.utcnow(),
        )
        await base.log(f"Pipeline complete. Final URL: {final_url}", agent="Orchestrator")

    except Exception as e:
        await base.log(str(e), level="error", agent="Orchestrator")
        await base.log_error("WF-001", "Orchestrator", str(e))
        await _update_video_status(db, video_id, "failed", error_message=str(e))
        raise


async def _process_scene(db: AsyncSession, video_id: str, scene: dict, voice_id: str) -> dict:
    scene_id = scene["scene_id"]
    base = BaseAgent(db, video_id)
    storage = StorageAgent(db, video_id)
    audio_agent = AudioAgent(db, video_id)
    image_agent = ImageAgent(db, video_id)
    video_agent = VideoAgent(db, video_id)

    try:
        await base.log(f"Processing scene {scene_id}", agent="Orchestrator")

        # Audio
        audio_bytes = await audio_agent.synthesize(scene["narration"], voice_id)
        audio_url = await storage.upload(
            f"audio/{video_id}/scene_{scene_id}.mp3", audio_bytes, "audio/mpeg")

        # SRT
        srt = await audio_agent.transcribe_to_srt(audio_bytes, scene["narration"], scene["duration_seconds"])

        # Image
        image_bytes = await image_agent.generate(scene["visual_description"])
        image_url = await storage.upload(
            f"images/{video_id}/scene_{scene_id}.png", image_bytes, "image/png")

        # Clip render
        clip_url = await video_agent.render_scene(image_url, audio_url, srt, scene["duration_seconds"])

        return {
            "scene_id": scene_id,
            "clip_url": clip_url,
            "audio_url": audio_url,
            "image_url": image_url,
            "srt_content": srt,
            "duration": scene["duration_seconds"],
            "status": "complete",
        }
    except Exception as e:
        await base.log(f"Scene {scene_id} failed: {e}", level="error", agent="Orchestrator")
        await base.log_error("WF-004", f"Scene-{scene_id}", str(e), scene_id=str(scene_id))
        return {"scene_id": scene_id, "status": "failed", "error": str(e)}
