"""Entry point for HuggingFace Spaces and local development."""
import os
from dotenv import load_dotenv

load_dotenv()

# Import app at module level so uvicorn can find it
from app.main import app  # noqa: F401, E402

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
