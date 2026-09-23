"""
Herramienta de lectura en Cosmos DB — operaciones tipadas, sin queries SQL-API libres
que el modelo pudiera manipular arbitrariamente.
"""
from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError
from fastapi import HTTPException

from config import get_settings

settings = get_settings()

_client: CosmosClient | None = None


def _get_client() -> CosmosClient:
    global _client
    if _client is None:
        _client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
    return _client


async def obtener_conversacion(user_id: str, conversation_id: str) -> dict:
    """Lee un único documento de conversación, particionado por userId (aislamiento por usuario)."""
    try:
        client = _get_client()
        db = client.get_database_client(settings.cosmos_database)
        container = db.get_container_client(settings.cosmos_container)
        item = await container.read_item(item=conversation_id, partition_key=user_id)
        return item
    except CosmosHttpResponseError as exc:
        if exc.status_code == 404:
            raise HTTPException(status_code=404, detail="Conversación no encontrada.") from exc
        raise HTTPException(status_code=502, detail=f"Error de Cosmos DB: {exc.message}") from exc


async def listar_conversaciones(user_id: str, limite: int = 20) -> list[dict]:
    """Lista las conversaciones de UN usuario (nunca cross-usuario: aislamiento por partición)."""
    try:
        client = _get_client()
        db = client.get_database_client(settings.cosmos_database)
        container = db.get_container_client(settings.cosmos_container)
        query = "SELECT TOP @limite * FROM c WHERE c.userId = @userId ORDER BY c._ts DESC"
        items = container.query_items(
            query=query,
            parameters=[{"name": "@limite", "value": limite}, {"name": "@userId", "value": user_id}],
            partition_key=user_id,
        )
        return [item async for item in items]
    except CosmosHttpResponseError as exc:
        raise HTTPException(status_code=502, detail=f"Error de Cosmos DB: {exc.message}") from exc
