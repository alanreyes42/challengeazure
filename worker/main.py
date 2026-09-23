"""
Worker de ingesta — expone /ingest, que el backend llama después de subir un
documento a Blob Storage. Orquesta: validar -> extraer -> chunking -> embeddings
-> indexar, de forma idempotente (recargar el mismo archivo no duplica chunks).
"""
import logging
import time

from fastapi import FastAPI
from pydantic import BaseModel

from blob_reader import validar_y_descargar
from chunking import generar_chunks
from doc_intelligence import extraer_contenido
from embeddings import generar_embeddings
from search_indexer import eliminar_chunks_previos, indexar_chunks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("worker.ingest")

app = FastAPI(title="DocuAssist Worker de Ingesta", version="1.0.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


class IngestRequest(BaseModel):
    blob_name: str          # ej. "usuario123/Politica_Devoluciones_2024.pdf"
    owner: str               # user_id del dueño del documento (para filtrado de seguridad en RAG)
    estrategia_chunking: str = "by_paragraph"  # o "fixed_size"


@app.post("/ingest")
async def ingest(req: IngestRequest):
    start = time.perf_counter()
    logger.info("ingest_start blob=%s owner=%s", req.blob_name, req.owner)

    # 1. Validar tipo/tamaño y descargar
    archivo_bytes = await validar_y_descargar(req.blob_name)

    # 2. Extraer contenido con Document Intelligence
    texto, num_paginas = await extraer_contenido(archivo_bytes)

    # 3. Chunking
    chunks = generar_chunks(texto, req.estrategia_chunking)
    # aproximación simple de página por chunk (proporcional a la posición del chunk)
    pagina_por_chunk = [
        min(num_paginas, max(1, round((i + 1) / len(chunks) * num_paginas))) for i in range(len(chunks))
    ]

    # 4. Embeddings
    vectores = await generar_embeddings(chunks)

    # 5. Idempotencia: borra chunks previos de este mismo documento antes de re-indexar
    await eliminar_chunks_previos(req.blob_name)

    # 6. Indexar
    indexados = await indexar_chunks(req.blob_name, req.owner, chunks, vectores, pagina_por_chunk)

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "ingest_done blob=%s chunks=%d indexados=%d duration_ms=%.0f",
        req.blob_name, len(chunks), indexados, duration_ms,
    )

    return {
        "blob_name": req.blob_name,
        "paginas": num_paginas,
        "chunks_generados": len(chunks),
        "chunks_indexados": indexados,
        "duration_ms": round(duration_ms),
    }
