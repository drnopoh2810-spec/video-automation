"""Entry point for HuggingFace Spaces and local development."""
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from app.main import app  # noqa

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
