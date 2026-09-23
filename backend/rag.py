"""
Nodo de recuperación RAG: convierte la pregunta en un vector, busca en AI Search
SOLO los chunks del usuario que pregunta (filtro `owner`), y devuelve los
fragmentos + su score de relevancia (para el nodo de validación de evidencia).
"""
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AsyncAzureOpenAI

from config import get_settings

settings = get_settings()


async def _embed_query(texto: str) -> list[float]:
    client = AsyncAzureOpenAI(
        azure_endpoint=settings.foundry_endpoint,
        api_key=settings.foundry_key,
        api_version="2024-08-01-preview",
    )
    response = await client.embeddings.create(model=settings.embeddings_deployment, input=[texto])
    return response.data[0].embedding


async def recuperar_contexto(pregunta: str, owner: str) -> list[dict]:
    """Devuelve una lista de {contenido, document_id, pagina, score}, aislado por owner."""
    vector = await _embed_query(pregunta)

    client = SearchClient(
        endpoint=settings.search_endpoint,
        index_name=settings.search_index_name,
        credential=AzureKeyCredential(settings.search_key),
    )
    try:
        results = await client.search(
            search_text=pregunta,
            vector_queries=[
                {
                    "kind": "vector",
                    "vector": vector,
                    "fields": "content_vector",
                    "k_nearest_neighbors": settings.rag_top_k,
                }
            ],
            filter=f"owner eq '{owner}'",
            select=["contenido", "document_id", "pagina"],
            top=settings.rag_top_k,
        )
        fragmentos = []
        async for doc in results:
            fragmentos.append(
                {
                    "contenido": doc["contenido"],
                    "document_id": doc["document_id"],
                    "pagina": doc["pagina"],
                    "score": doc.get("@search.score", 0.0),
                }
            )
        return fragmentos
    finally:
        await client.close()
