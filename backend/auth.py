"""
Valida el JWT del USUARIO FINAL (emitido por Entra ID al hacer login en el
frontend), a diferencia de tools-api que valida el token del backend como
servicio. Aquí además extraemos el user_id real para aislar RAG y memoria.
"""
import time
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

from config import get_settings

settings = get_settings()
JWKS_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"


@lru_cache
def _get_jwk_client() -> PyJWKClient:
    return PyJWKClient(JWKS_URL_TEMPLATE.format(tenant_id=settings.entra_tenant_id))


async def verify_user_token(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta Bearer token.")
    token = authorization.removeprefix("Bearer ").strip()

    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.entra_audience,
            options={"require": ["exp", "iat", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Token inválido: {exc}") from exc

    if claims.get("exp", 0) < time.time():
        raise HTTPException(status_code=401, detail="Token expirado")

    # Roles asignados en Entra ID (App Roles) — usados para autorización de operaciones sensibles
    claims["app_roles"] = claims.get("roles", [])
    return claims
