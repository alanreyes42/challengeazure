"""
API de Herramientas — expone operaciones tipadas y validadas que el agente
(LangGraph, en el backend) puede invocar como "tools". Nunca ejecuta SQL libre
generado por el modelo. Solo es alcanzable desde dentro del clúster (namespace
backend -> tools-api), nunca expuesta públicamente vía Ingress.
"""
import time

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel, Field

from audit import enforce_rate_limit, log_tool_call
from auth import verify_bearer_token
from tools_cosmos import listar_conversaciones, obtener_conversacion
from tools_sql import consultar_tabla

app = FastAPI(
    title="DocuAssist Tools API",
    description="Operaciones controladas de datos para el agente (SQL parametrizado, Cosmos DB).",
    version="1.0.0",
)


@app.get("/health")
async def health():
    """Usado por los probes de Kubernetes (liveness/readiness), sin auth."""
    return {"status": "ok"}


class ConsultaSQLRequest(BaseModel):
    tabla: str = Field(..., description="Nombre de tabla, debe estar en la whitelist.")
    filtros: dict[str, str | int | bool] = Field(default_factory=dict)


@app.post("/tools/sql/consultar")
async def sql_consultar(req: ConsultaSQLRequest, claims: dict = Depends(verify_bearer_token)):
    subject = claims.get("sub", claims.get("azp", "desconocido"))
    enforce_rate_limit(subject)
    start = time.perf_counter()
    try:
        resultado = await consultar_tabla(req.tabla, req.filtros)
        status_code = 200
        return {"filas": resultado, "total": len(resultado)}
    finally:
        log_tool_call(subject, "sql.consultar", req.model_dump(), status_code, (time.perf_counter() - start) * 1000)


class ConversacionRequest(BaseModel):
    user_id: str
    conversation_id: str


@app.post("/tools/cosmos/conversacion")
async def cosmos_obtener(req: ConversacionRequest, claims: dict = Depends(verify_bearer_token)):
    subject = claims.get("sub", claims.get("azp", "desconocido"))
    enforce_rate_limit(subject)
    start = time.perf_counter()
    try:
        resultado = await obtener_conversacion(req.user_id, req.conversation_id)
        status_code = 200
        return resultado
    finally:
        log_tool_call(subject, "cosmos.obtener", req.model_dump(), status_code, (time.perf_counter() - start) * 1000)


class ListarConversacionesRequest(BaseModel):
    user_id: str
    limite: int = Field(default=20, le=100)


@app.post("/tools/cosmos/conversaciones")
async def cosmos_listar(req: ListarConversacionesRequest, claims: dict = Depends(verify_bearer_token)):
    subject = claims.get("sub", claims.get("azp", "desconocido"))
    enforce_rate_limit(subject)
    start = time.perf_counter()
    try:
        resultado = await listar_conversaciones(req.user_id, req.limite)
        status_code = 200
        return {"conversaciones": resultado, "total": len(resultado)}
    finally:
        log_tool_call(subject, "cosmos.listar", req.model_dump(), status_code, (time.perf_counter() - start) * 1000)
