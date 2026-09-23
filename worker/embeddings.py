"""
Genera embeddings vectoriales para cada chunk, usando el deployment de
text-embedding-3-small en Azure AI Foundry.
"""
from openai import AsyncAzureOpenAI
from fastapi import HTTPException

from config import get_settings

settings = get_settings()

_client: AsyncAzureOpenAI | None = None


def _get_client() -> AsyncAzureOpenAI:
    global _client
    if _client is None:
        _client = AsyncAzureOpenAI(
            azure_endpoint=settings.foundry_endpoint,
            api_key=settings.foundry_key,
            api_version="2024-08-01-preview",
        )
    return _client


async def generar_embeddings(chunks: list[str]) -> list[list[float]]:
    """Genera embeddings en lotes (batching) para eficiencia — la API de embeddings acepta arrays."""
    client = _get_client()
    try:
        response = await client.embeddings.create(
            model=settings.embeddings_deployment,
            input=chunks,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error generando embeddings: {exc}") from exc

    return [item.embedding for item in response.data]
