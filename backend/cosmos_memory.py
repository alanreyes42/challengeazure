"""
Memoria conversacional en Cosmos DB — particionado por userId (mismo patrón de
aislamiento que usa tools_cosmos.py en la API de herramientas).
"""
from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

from config import get_settings

settings = get_settings()

_client: CosmosClient | None = None


def _get_client() -> CosmosClient:
    global _client
    if _client is None:
        _client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
    return _client


async def obtener_historial(user_id: str, conversation_id: str, max_turnos: int = 10) -> list[dict]:
    """Lee los últimos N turnos de la conversación. Devuelve [] si no existe (conversación nueva)."""
    try:
        container = _get_client().get_database_client(settings.cosmos_database).get_container_client(
            settings.cosmos_container
        )
        item = await container.read_item(item=conversation_id, partition_key=user_id)
        return item.get("turnos", [])[-max_turnos:]
    except CosmosHttpResponseError as exc:
        if exc.status_code == 404:
            return []
        raise


async def guardar_turno(user_id: str, conversation_id: str, pregunta: str, respuesta: str, citas: list[dict]) -> None:
    """Agrega un turno (pregunta+respuesta+citas) al documento de la conversación (upsert)."""
    container = _get_client().get_database_client(settings.cosmos_database).get_container_client(
        settings.cosmos_container
    )
    try:
        item = await container.read_item(item=conversation_id, partition_key=user_id)
    except CosmosHttpResponseError as exc:
        if exc.status_code != 404:
            raise
        item = {"id": conversation_id, "userId": user_id, "turnos": []}

    item["turnos"].append({"pregunta": pregunta, "respuesta": respuesta, "citas": citas})
    await container.upsert_item(item)
