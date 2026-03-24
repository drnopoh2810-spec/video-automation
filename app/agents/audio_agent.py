"""WF-004 Audio: ElevenLabs TTS + Groq Whisper SRT."""
import httpx
from app.agents.base import BaseAgent
from app.agents.account_selector import get_account


class AudioAgent(BaseAgent):
    ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"
    GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

    async def synthesize(self, narration: str, voice_id: str) -> bytes:
        await self.log(f"Synthesizing audio for scene", agent="AudioAgent")
        account = await get_account(self.db, "elevenlabs")
        if not account["api_key"]:
            raise ValueError("No ElevenLabs API key configured")

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.ELEVENLABS_URL}/{voice_id}",
                headers={"xi-api-key": account["api_key"], "Content-Type": "application/json", "Accept": "audio/mpeg"},
                json={"text": narration, "model_id": "eleven_multilingual_v2",
                      "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
            )
            resp.raise_for_status()
        return resp.content

    async def transcribe_to_srt(self, audio_bytes: bytes, narration: str, duration: int) -> str:
        """Transcribe audio to SRT using Groq Whisper, fallback to manual SRT."""
        account = await get_account(self.db, "groq")
        if not account["api_key"]:
            return self._fallback_srt(narration, duration)

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(
                    self.GROQ_WHISPER_URL,
                    headers={"Authorization": f"Bearer {account['api_key']}"},
                    files={"file": ("audio.mp3", audio_bytes, "audio/mpeg")},
                    data={"model": "whisper-large-v3", "response_format": "srt", "language": "en"},
                )
                resp.raise_for_status()
            return resp.text
        except Exception:
            return self._fallback_srt(narration, duration)

    def _fallback_srt(self, narration: str, duration: int) -> str:
        d = str(duration).zfill(2)
        return f"1\n00:00:00,000 --> 00:00:{d},000\n{narration}\n"
