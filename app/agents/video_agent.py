"""WF-005 & WF-006: Creatomate video rendering agent."""
import asyncio
import httpx
from app.agents.base import BaseAgent
from app.agents.account_selector import get_account

CREATOMATE_URL = "https://api.creatomate.com/v1/renders"


class VideoAgent(BaseAgent):
    async def render_scene(self, image_url: str, audio_url: str, srt: str, duration: int) -> str:
        """Render a single scene clip. Returns output URL."""
        await self.log("Rendering scene clip via Creatomate", agent="VideoAgent")
        account = await get_account(self.db, "creatomate")
        if not account["api_key"]:
            raise ValueError("No Creatomate API key configured")

        payload = {
            "output_format": "mp4", "width": 1280, "height": 720, "frame_rate": 30,
            "elements": [
                {"type": "image", "source": image_url, "duration": duration,
                 "animations": [{"type": "scale", "scope": "element", "easing": "linear",
                                 "start_scale": "100%", "end_scale": "110%"}]},
                {"type": "audio", "source": audio_url, "duration": duration},
                {"type": "subtitles", "source": srt, "font_family": "Arial",
                 "font_size": "5 vmin", "font_weight": "700", "color": "#FFFFFF",
                 "background_color": "rgba(0,0,0,0.5)", "x_alignment": "50%", "y_alignment": "85%"},
            ],
        }
        return await self._submit_and_poll(account["api_key"], payload)

    async def concatenate_clips(self, clip_urls: list[str]) -> str:
        """Concatenate all scene clips into final video. Returns output URL."""
        await self.log(f"Concatenating {len(clip_urls)} clips", agent="VideoAgent")
        account = await get_account(self.db, "creatomate")
        if not account["api_key"]:
            raise ValueError("No Creatomate API key configured")

        payload = {
            "output_format": "mp4", "width": 1280, "height": 720, "frame_rate": 30,
            "elements": [{"type": "video", "source": url, "trim_start": 0} for url in clip_urls],
        }
        return await self._submit_and_poll(account["api_key"], payload, max_polls=60, poll_interval=10)

    async def _submit_and_poll(self, api_key: str, payload: dict,
                                max_polls: int = 60, poll_interval: int = 5) -> str:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(CREATOMATE_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            render = data[0] if isinstance(data, list) else data
            job_id = render["id"]
            output_url = render.get("url")
            status = (render.get("status") or "").lower()

        for _ in range(max_polls):
            if status == "succeeded" and output_url:
                return output_url
            await asyncio.sleep(poll_interval)
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{CREATOMATE_URL}/{job_id}", headers=headers)
                resp.raise_for_status()
                data = resp.json()
                status = (data.get("status") or "").lower()
                output_url = data.get("url") or output_url

        raise TimeoutError(f"Render job {job_id} timed out after {max_polls} polls")
