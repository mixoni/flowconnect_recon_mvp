from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    ai_api_key: str | None = os.getenv("AI_API_KEY")

settings = Settings()
