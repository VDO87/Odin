"""Configurações do Odin Zero."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

API_KEY = os.getenv("API_KEY", "")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_PATH = Path(os.getenv("LOG_PATH", "logs"))
SEED = int(os.getenv("SEED", "0"))
