"""
El backend actúa como client OAuth2 (client_credentials flow) para llamar a
tools-api con su PROPIA identidad de servicio — nunca reenvía el token del
usuario final, así tools-api siempre sabe que quien llama es el backend.
"""
import time

import httpx

from config import get_settings

settings = get_settings()

_cached_token: str | None = None
_cached_expiry: float = 0


async def get_service_token() -> str:
    global _cached_token, _cached_expiry
    if _cached_token and time.time() < _cached_expiry - 60:
        return _cached_token

    url = f"https://login.microsoftonline.com/{settings.entra_tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.entra_client_id,
        "client_secret": settings.entra_client_secret,
        "scope": f"{settings.entra_audience}/.default",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, data=data)
        response.raise_for_status()
        payload = response.json()

    _cached_token = payload["access_token"]
    _cached_expiry = time.time() + payload.get("expires_in", 3600)
    return _cached_token
