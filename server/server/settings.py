import os
from pathlib import Path

from core.config.dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env")

# ponytail: sin auth/usuarios, no hay datos que proteger con esta key
SECRET_KEY = "llm-lab-server-local-only"
DEBUG = os.environ.get("LLM_LAB_SERVER_DEBUG", "0") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "llm",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "server.urls"
ASGI_APPLICATION = "server.asgi.application"

CORS_ALLOWED_ORIGINS = [
    origin
    for origin in os.environ.get(
        "LLM_LAB_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin
]
CORS_ALLOW_METHODS = ["GET", "POST", "OPTIONS"]

USE_TZ = True

# ponytail: sin modelos Django reales (el estado vive en data/memory.db via
# core.memory), sqlite en memoria solo para que el framework arranque.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
