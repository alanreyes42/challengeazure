"""
Chunking del texto extraído. El reto pide al menos dos estrategias — aquí:
1. fixed_size: ventana fija de tokens con overlap (robusta, funciona en cualquier texto).
2. by_paragraph: respeta límites de párrafo, agrupando hasta el tamaño objetivo
   (mejor coherencia semántica cuando el documento tiene estructura clara).
"""
import re

from config import get_settings

settings = get_settings()

# Aproximación simple: ~4 caracteres por token (evita traer un tokenizer pesado al worker)
CHARS_PER_TOKEN = 4


def chunk_fixed_size(texto: str) -> list[str]:
    chunk_chars = settings.chunk_size_tokens * CHARS_PER_TOKEN
    overlap_chars = settings.chunk_overlap_tokens * CHARS_PER_TOKEN

    chunks = []
    start = 0
    while start < len(texto):
        end = start + chunk_chars
        chunks.append(texto[start:end])
        start = end - overlap_chars
    return [c.strip() for c in chunks if c.strip()]


def chunk_by_paragraph(texto: str) -> list[str]:
    chunk_chars = settings.chunk_size_tokens * CHARS_PER_TOKEN
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 1 <= chunk_chars:
            current = f"{current}\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


def generar_chunks(texto: str, estrategia: str = "by_paragraph") -> list[str]:
    if estrategia == "fixed_size":
        return chunk_fixed_size(texto)
    return chunk_by_paragraph(texto)
