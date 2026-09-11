"""
Central application configuration.
All values are read from environment variables so no secrets are hardcoded
or committed to the repository. See .env.example for the full list.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- LLM (Gemini) ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # --- File validation ---
    MAX_PAGES: int = int(os.getenv("MAX_PAGES", "3"))
    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "15"))

    # --- OCR ---
    OCR_DPI: int = int(os.getenv("OCR_DPI", "200"))

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/documents.db")

    # --- Storage ---
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./data/uploads")

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "./data/app.log")


settings = Settings()
