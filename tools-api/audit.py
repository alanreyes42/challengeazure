"""
Auditoría (requisito del reto: registrar cargas, consultas y llamadas a herramientas)
y rate limiting básico en memoria (para producción real, mover a Redis compartido).
"""
import logging
import time
from collections import defaultdict, deque

from fastapi import HTTPException

from config import get_settings

settings = get_settings()

logger = logging.getLogger("tools_api.audit")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ventana deslizante simple por sujeto (claim "sub" del JWT del backend)
_calls_by_subject: dict[str, deque] = defaultdict(deque)


def log_tool_call(subject: str, tool: str, params: dict, status_code: int, duration_ms: float) -> None:
    """Registro estructurado — en AKS esto sale a stdout y lo recoge Azure Monitor/Log Analytics."""
    logger.info(
        "tool_call subject=%s tool=%s params=%s status=%s duration_ms=%.1f",
        subject, tool, {k: v for k, v in params.items() if k != "password"}, status_code, duration_ms,
    )


def enforce_rate_limit(subject: str) -> None:
    """Lanza 429 si el sujeto excede rate_limit_per_minute llamadas en la ventana de 60s."""
    now = time.time()
    window = _calls_by_subject[subject]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Límite de solicitudes excedido. Intenta más tarde.")
    window.append(now)
