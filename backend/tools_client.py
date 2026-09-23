"""
Cliente hacia la API de Herramientas. El modelo NUNCA construye la llamada
directa — LangGraph decide invocar una tool tipada, y este cliente es el único
punto que realmente cruza la red hacia tools-api, siempre con el token de
servicio del backend (nunca con credenciales del modelo ni del usuario).
"""
import httpx

from config import get_settings
from service_token import get_service_token

settings = get_settings()


async def consultar_sql(tabla: str, filtros: dict) -> dict:
    token = await get_service_token()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.tools_api_url}/tools/sql/consultar",
            json={"tabla": tabla, "filtros": filtros},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()
