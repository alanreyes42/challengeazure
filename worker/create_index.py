"""
Crea el índice de Azure AI Search (correr UNA VEZ, no es parte del flujo normal
del worker). Define campos de texto, metadatos, y un campo vectorial con
búsqueda HNSW para similitud semántica.

Uso: python create_index.py
"""
import asyncio

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
)

from config import get_settings

settings = get_settings()

EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small


async def crear_indice():
    client = SearchIndexClient(
        endpoint=settings.search_endpoint,
        credential=AzureKeyCredential(settings.search_key),
    )

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="owner", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="pagina", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SearchableField(name="contenido", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="default-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="default-hnsw")],
        profiles=[VectorSearchProfile(name="default-profile", algorithm_configuration_name="default-hnsw")],
    )

    index = SearchIndex(name=settings.search_index_name, fields=fields, vector_search=vector_search)

    async with client:
        result = await client.create_or_update_index(index)
        print(f"Índice '{result.name}' creado/actualizado con {len(result.fields)} campos.")


if __name__ == "__main__":
    asyncio.run(crear_indice())
