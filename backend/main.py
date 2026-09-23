"""
Backend/orquestador — expone /chat, que ejecuta el grafo de LangGraph completo:
clasificación, RAG o tool, validación de evidencia, generación, con memoria
conversacional persistida en Cosmos DB por usuario.
"""
import logging
import time

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth import verify_user_token
from cosmos_memory import guardar_turno, obtener_historial
from documents import router as documents_router
from graph import get_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backend.chat")

app = FastAPI(title="DocuAssist Backend/Orquestador", version="1.0.0")
app.include_router(documents_router)

# CORS: solo los dos frontends autorizados (ajustar dominios reales cuando existan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-assistant.alaniatest.lat",
        "https://app-ai-assistant.alaniatest.lat",
        "https://app-ai-assistant-docuassist.azurewebsites.net",
        "http://localhost:4200",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    conversation_id: str
    mensaje: str


@app.post("/chat")
async def chat(req: ChatRequest, claims: dict = Depends(verify_user_token)):
    user_id = claims.get("oid") or claims.get("sub")
    start = time.perf_counter()
    logger.info("chat_start user=%s conversation=%s", user_id, req.conversation_id)

    historial = await obtener_historial(user_id, req.conversation_id)

    graph = get_graph()
    resultado = await graph.ainvoke(
        {
            "pregunta": req.mensaje,
            "user_id": user_id,
            "historial": historial,
            "intentos": 0,
        }
    )

    await guardar_turno(
        user_id, req.conversation_id, req.mensaje, resultado["respuesta"], resultado.get("citas", [])
    )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("chat_done user=%s duration_ms=%.0f ruta=%s", user_id, duration_ms, resultado.get("ruta"))

    return {
        "respuesta": resultado["respuesta"],
        "citas": resultado.get("citas", []),
        "ruta_tomada": resultado.get("ruta"),
    }
