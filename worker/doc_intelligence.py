"""
Extracción de texto/tablas/estructura vía Azure AI Document Intelligence.
Equivalente a Document AI de GCP.
"""
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from fastapi import HTTPException

from config import get_settings

settings = get_settings()


async def extraer_contenido(archivo_bytes: bytes) -> tuple[str, int]:
    """
    Devuelve (texto_completo, numero_de_paginas).
    Usa el modelo prebuilt-layout (extrae texto + estructura + tablas).
    """
    client = DocumentIntelligenceClient(
        endpoint=settings.docintel_endpoint.rstrip("/"),
        credential=AzureKeyCredential(settings.docintel_key),
    )
    try:
        poller = await client.begin_analyze_document(
            "prebuilt-layout", archivo_bytes, content_type="application/octet-stream"
        )
        result = await poller.result()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error de Document Intelligence: {exc}") from exc
    finally:
        await client.close()

    if not result.content:
        raise HTTPException(status_code=422, detail="El documento no produjo contenido extraíble.")

    num_paginas = len(result.pages) if result.pages else 1
    return result.content, num_paginas
