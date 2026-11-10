"""
Configuration for Rewind backend.
Reads from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/rewind.db")

# Server
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8081"))
RELOAD: bool = os.getenv("RELOAD", "true").lower() == "true"

# CORS — allowed origins for local development
ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:5174",
    ).split(",")
    if o.strip()
]

# LLM (optional — diagnosis uses this when available)
LLM_API_KEY: str | None = os.getenv("LLM_API_KEY")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")  # "google" | "openai" | "anthropic"

# Safety limits
MAX_STEPS: int = int(os.getenv("MAX_STEPS", "50"))
MAX_REPLAY_STEPS: int = int(os.getenv("MAX_REPLAY_STEPS", "50"))
