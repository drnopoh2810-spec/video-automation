"""WF-004 Image: HuggingFace Stable Diffusion image generation."""
import httpx
from app.agents.base import BaseAgent
from app.agents.account_selector import get_account

HF_MODEL_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"


class ImageAgent(BaseAgent):
    async def generate(self, visual_description: str) -> bytes:
        await self.log(f"Generating image for scene", agent="ImageAgent")
        account = await get_account(self.db, "huggingface")
        if not account["api_key"]:
            raise ValueError("No HuggingFace API key configured")

        prompt = visual_description + ", high quality, cinematic, 4k, detailed"
        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": "blurry, low quality, distorted, ugly, watermark",
                "width": 1280, "height": 720,
                "num_inference_steps": 20, "guidance_scale": 7,
            },
        }

        async with httpx.AsyncClient(timeout=180) as client:
            for attempt in range(3):
                resp = await client.post(
                    HF_MODEL_URL,
                    headers={"Authorization": f"Bearer {account['api_key']}"},
                    json=payload,
                )
                if resp.status_code == 503:
                    # Model loading, wait and retry
                    import asyncio
                    await asyncio.sleep(20)
                    continue
                resp.raise_for_status()
                return resp.content

        raise RuntimeError("HuggingFace model unavailable after 3 attempts")
