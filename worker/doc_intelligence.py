"""
Extracción de texto/tablas/estructura vía Azure AI Document Intelligence.
Equivalente a Document AI de GCP.

Nota: este recurso solo soporta la ruta legacy /formrecognizer/ (capability
"FormRecognizer", no "DocumentIntelligence"), por lo que usamos el SDK
azure-ai-formrecognizer en vez del SDK nuevo azure-ai-documentintelligence,
que solo sabe hablar con la ruta /documentintelligence/.
"""
from azure.ai.formrecognizer.aio import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from fastapi import HTTPException

from config import get_settings

settings = get_settings()


async def extraer_contenido(archivo_bytes: bytes) -> tuple[str, int]:
    """
    Devuelve (texto_completo, numero_de_paginas).
    Usa el modelo prebuilt-layout (extrae texto + estructura + tablas).
    """
    client = DocumentAnalysisClient(
        endpoint=settings.docintel_endpoint.rstrip("/"),
        credential=AzureKeyCredential(settings.docintel_key),
    )
    try:
        poller = await client.begin_analyze_document("prebuilt-layout", document=archivo_bytes)
        result = await poller.result()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error de Document Intelligence: {exc}") from exc
    finally:
        await client.close()

    if not result.content:
        # El SDK legacy puede no exponer 'content' directo en algunas versiones;
        # se reconstruye concatenando las líneas de cada página como fallback.
        lineas = []
        for page in result.pages or []:
            for line in page.lines or []:
                lineas.append(line.content)
        contenido = "\n".join(lineas)
        if not contenido:
            raise HTTPException(status_code=422, detail="El documento no produjo contenido extraíble.")
    else:
        contenido = result.content

    num_paginas = len(result.pages) if result.pages else 1
    return contenido, num_paginas
