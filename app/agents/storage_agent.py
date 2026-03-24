"""Supabase storage agent for uploading assets."""
import httpx
from app.agents.base import BaseAgent
from app.agents.account_selector import get_account


class StorageAgent(BaseAgent):
    async def upload(self, path: str, data: bytes, content_type: str) -> str:
        """Upload bytes to Supabase storage. Returns public URL."""
        account = await get_account(self.db, "supabase")
        if not account["api_key"] or not account["extra"].get("url"):
            raise ValueError("No Supabase credentials configured")

        base_url = account["extra"]["url"].rstrip("/")
        bucket = "video-assets"
        upload_url = f"{base_url}/storage/v1/object/{bucket}/{path}"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                upload_url,
                headers={"Authorization": f"Bearer {account['api_key']}",
                         "Content-Type": content_type, "x-upsert": "true"},
                content=data,
            )
            resp.raise_for_status()

        return f"{base_url}/storage/v1/object/public/{bucket}/{path}"
