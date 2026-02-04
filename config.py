from __future__ import annotations

import os

APP_TITLE = "Tablero Metricas de Callcenter"

API_BASE_URL = os.getenv("API_BASE_URL", "http://192.168.100.127:3000")
DEFAULT_MAX_SECONDS = int(os.getenv("FRT_MAX_SECONDS", "300"))
DEFAULT_FRT_LIMIT = int(os.getenv("FRT_LIMIT", "10"))
