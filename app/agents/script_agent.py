"""WF-002: Script Generation Agent using Groq LLM."""
import json
import httpx
from app.agents.base import BaseAgent
from app.agents.account_selector import get_account


class ScriptAgent(BaseAgent):
    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL = "llama3-70b-8192"

    async def generate(self, title: str, niche: str, duration: int) -> dict:
        await self.log(f"Generating script for: {title}", agent="ScriptAgent")
        account = await get_account(self.db, "groq")
        if not account["api_key"]:
            raise ValueError("No Groq API key configured")

        scene_count = max(1, duration // 15)
        prompt = self._build_prompt(title, niche, duration, scene_count)

        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                self.GROQ_URL,
                headers={"Authorization": f"Bearer {account['api_key']}", "Content-Type": "application/json"},
                json={"model": self.MODEL, "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.7, "max_tokens": 4096},
            )
            resp.raise_for_status()

        raw = resp.json()["choices"][0]["message"]["content"]
        script = self._parse_script(raw)
        self._validate(script)
        await self.log(f"Script ready: {len(script['scenes'])} scenes", agent="ScriptAgent")
        return script

    def _build_prompt(self, title, niche, duration, scene_count):
        return f"""You are a professional YouTube scriptwriter specializing in {niche} content.
Create a complete video script for: "{title}"
Target duration: {duration} seconds (~{scene_count} scenes of ~15s each)

Return ONLY valid JSON:
{{
  "title": "video title",
  "total_duration": {duration},
  "scenes": [
    {{
      "scene_id": 1,
      "act": 1,
      "narration": "spoken text (15-20 words)",
      "visual_description": "detailed image prompt for Stable Diffusion",
      "duration_seconds": 15,
      "keywords": ["keyword1", "keyword2"]
    }}
  ]
}}
Acts: 1=intro, 2=main, 3=outro. Generate exactly {scene_count} scenes. Return ONLY JSON."""

    def _parse_script(self, raw: str) -> dict:
        raw = raw.strip()
        for prefix in ["```json", "```"]:
            if raw.startswith(prefix):
                raw = raw[len(prefix):]
        raw = raw.rstrip("`").strip()
        match = __import__("re").search(r"\{[\s\S]*\}", raw)
        if match:
            raw = match.group(0)
        return json.loads(raw)

    def _validate(self, script: dict):
        issues = []
        if not script.get("title"):
            issues.append("Missing title")
        scenes = script.get("scenes", [])
        if not scenes:
            issues.append("No scenes")
        for i, s in enumerate(scenes):
            for field in ["scene_id", "narration", "visual_description", "duration_seconds"]:
                if not s.get(field):
                    issues.append(f"Scene {i}: missing {field}")
        if issues:
            raise ValueError("Script validation failed: " + "; ".join(issues))
