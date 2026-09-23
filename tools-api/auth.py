"""
Autenticación: valida que la llamada venga realmente del backend/orquestador,
verificando el JWT emitido por Microsoft Entra ID (OAuth2 client-credentials flow
entre backend y tools-api, tráfico que además solo es alcanzable dentro del clúster).
"""
import time
from functools import lru_cache

import httpx
import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

from config import get_settings

settings = get_settings()

JWKS_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"


@lru_cache
def _get_jwk_client() -> PyJWKClient:
    url = JWKS_URL_TEMPLATE.format(tenant_id=settings.entra_tenant_id)
    return PyJWKClient(url)


async def verify_bearer_token(authorization: str = Header(...)) -> dict:
    """
    Dependency de FastAPI: exige un header `Authorization: Bearer <jwt>` válido,
    emitido por el tenant de Entra ID configurado, con la audiencia esperada.
    Rechaza cualquier llamada sin token válido (incluida la del propio modelo,
    que nunca debe poder llamar esta API directo — solo el backend puede).
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el header Authorization: Bearer <token>",
        )
    token = authorization.removeprefix("Bearer ").strip()

    try:
        jwk_client = _get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.entra_audience,
            options={"require": ["exp", "iat", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {exc}",
        ) from exc

    if claims.get("exp", 0) < time.time():
        raise HTTPException(status_code=401, detail="Token expirado")

    return claims
