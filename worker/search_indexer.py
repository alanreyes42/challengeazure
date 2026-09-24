"""
Indexa los chunks + embeddings en Azure AI Search.
Idempotencia: antes de indexar, borra cualquier chunk previo del MISMO documento
(identificado por document_id, ej. el nombre del blob), así recargar el mismo
archivo no genera duplicados.
"""
import hashlib

from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from fastapi import HTTPException

from config import get_settings

settings = get_settings()


def _get_client() -> SearchClient:
    return SearchClient(
        endpoint=settings.search_endpoint,
        index_name=settings.search_index_name,
        credential=AzureKeyCredential(settings.search_key),
    )


def _chunk_id(document_id: str, index: int) -> str:
    """ID determinístico por documento+posición — mismo archivo siempre genera los mismos IDs."""
    raw = f"{document_id}::{index}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def eliminar_chunks_previos(document_id: str) -> None:
    client = _get_client()
    try:
        results = await client.search(search_text="*", filter=f"document_id eq '{document_id}'", select=["id"])
        ids_a_borrar = [{"id": doc["id"]} async for doc in results]
        if ids_a_borrar:
            await client.delete_documents(documents=ids_a_borrar)
    finally:
        await client.close()


async def indexar_chunks(
    document_id: str,
    owner: str,
    chunks: list[str],
    embeddings: list[list[float]],
    pagina_por_chunk: list[int],
) -> int:
    """Indexa (upsert) los chunks nuevos. Devuelve cuántos se indexaron."""
    if len(chunks) != len(embeddings):
        raise HTTPException(status_code=500, detail="Desalineación entre chunks y embeddings.")

    documentos = [
        {
            "id": _chunk_id(document_id, i),
            "document_id": document_id,
            "owner": owner,
            "pagina": pagina_por_chunk[i],
            "contenido": chunk,
            "content_vector": embeddings[i],
        }
        for i, chunk in enumerate(chunks)
    ]

    client = _get_client()
    try:
        result = await client.merge_or_upload_documents(documents=documentos)
        exitosos = sum(1 for r in result if r.succeeded)
        return exitosos
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error indexando en AI Search: {exc}") from exc
    finally:
        await client.close()
