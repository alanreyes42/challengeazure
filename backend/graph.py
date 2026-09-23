"""
Grafo del agente (LangGraph). Nodos mínimos que pide el reto:
  clasificación/enrutamiento -> recuperación RAG -> ejecución de herramientas
  -> generación de respuesta -> validación de evidencia -> manejo de error/reintento
  -> ruta de "no tengo información suficiente"

Principio anti-alucinación: el nodo `validar_evidencia` es OBLIGATORIO antes de
devolver cualquier respuesta que dependa de RAG — si el score de los fragmentos
recuperados no supera el umbral, se fuerza la ruta "sin_informacion", nunca se
deja que el modelo "rellene" con conocimiento propio no verificable.
"""
from typing import TypedDict

from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, END

from config import get_settings
from rag import recuperar_contexto
from tools_client import consultar_sql

settings = get_settings()


class AgentState(TypedDict, total=False):
    pregunta: str
    user_id: str
    historial: list[dict]
    ruta: str                  # "rag" | "tool" | "directo"
    fragmentos: list[dict]
    evidencia_suficiente: bool
    tool_resultado: dict | None
    respuesta: str
    citas: list[dict]
    intentos: int
    error: str | None


def _get_llm(deployment: str, temperature: float = 0.0) -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=settings.foundry_endpoint,
        api_key=settings.foundry_key,
        api_version="2024-08-01-preview",
        azure_deployment=deployment,
        temperature=temperature,
    )


# ---------- Nodo 1: clasificación / enrutamiento ----------
async def nodo_clasificar(state: AgentState) -> AgentState:
    llm = _get_llm(settings.router_model_deployment)
    prompt = (
        "Clasifica la intención de la pregunta del usuario en UNA sola palabra:\n"
        "- 'rag' si pregunta sobre contenido de documentos (políticas, procesos, información general)\n"
        "- 'tool' si pide datos estructurados/transaccionales (pedidos, inventario, clientes)\n"
        "- 'directo' si es un saludo o pregunta que no requiere buscar nada\n\n"
        f"Pregunta: {state['pregunta']}\n\nResponde solo con: rag, tool o directo."
    )
    result = await llm.ainvoke(prompt)
    ruta = result.content.strip().lower()
    return {"ruta": ruta if ruta in ("rag", "tool", "directo") else "rag"}


# ---------- Nodo 2: recuperación RAG ----------
async def nodo_rag(state: AgentState) -> AgentState:
    try:
        fragmentos = await recuperar_contexto(state["pregunta"], state["user_id"])
        return {"fragmentos": fragmentos, "error": None}
    except Exception as exc:  # noqa: BLE001 — nodo de manejo de error captura cualquier falla de RAG
        return {"fragmentos": [], "error": f"error_rag: {exc}"}


# ---------- Nodo 3: ejecución de herramientas ----------
async def nodo_tool(state: AgentState) -> AgentState:
    try:
        # En una versión completa, un LLM decidiría tabla/filtros; aquí se deja explícito
        # como ejemplo mínimo demostrable — el punto de seguridad es tools_client/tools-api.
        resultado = await consultar_sql(tabla="pedidos", filtros={"cliente_id": state["user_id"]})
        return {"tool_resultado": resultado, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"tool_resultado": None, "error": f"error_tool: {exc}"}


# ---------- Nodo 4: validación de evidencia (anti-alucinación) ----------
async def nodo_validar_evidencia(state: AgentState) -> AgentState:
    fragmentos = state.get("fragmentos", [])
    if not fragmentos:
        return {"evidencia_suficiente": False}
    mejor_score = max(f["score"] for f in fragmentos)
    return {"evidencia_suficiente": mejor_score >= settings.min_search_score}


# ---------- Nodo 5a: generación con evidencia (RAG) ----------
async def nodo_generar_rag(state: AgentState) -> AgentState:
    llm = _get_llm(settings.gen_model_deployment)
    contexto = "\n\n".join(
        f"[Fuente: {f['document_id']}, página {f['pagina']}]\n{f['contenido']}" for f in state["fragmentos"]
    )
    prompt = (
        "Responde la pregunta del usuario ÚNICAMENTE con la información del contexto. "
        "Si el contexto no contiene la respuesta, dilo explícitamente. Cita la fuente al final.\n\n"
        f"Contexto:\n{contexto}\n\nPregunta: {state['pregunta']}"
    )
    result = await llm.ainvoke(prompt)
    citas = [{"document_id": f["document_id"], "pagina": f["pagina"]} for f in state["fragmentos"]]
    return {"respuesta": result.content, "citas": citas}


# ---------- Nodo 5b: generación con resultado de tool ----------
async def nodo_generar_tool(state: AgentState) -> AgentState:
    llm = _get_llm(settings.gen_model_deployment)
    prompt = (
        f"Resume en lenguaje natural este resultado de una consulta de datos, "
        f"respondiendo la pregunta original del usuario.\n\n"
        f"Pregunta: {state['pregunta']}\nDatos: {state['tool_resultado']}"
    )
    result = await llm.ainvoke(prompt)
    return {"respuesta": result.content, "citas": []}


# ---------- Nodo 5c: respuesta directa (saludo, sin RAG/tool) ----------
async def nodo_generar_directo(state: AgentState) -> AgentState:
    llm = _get_llm(settings.gen_model_deployment)
    result = await llm.ainvoke(state["pregunta"])
    return {"respuesta": result.content, "citas": []}


# ---------- Nodo 6: sin información suficiente ----------
async def nodo_sin_informacion(state: AgentState) -> AgentState:
    return {
        "respuesta": "No tengo información suficiente en tus documentos para responder esto con confianza. "
        "¿Podrías subir un documento relacionado o reformular la pregunta?",
        "citas": [],
    }


# ---------- Nodo 7: manejo de error ----------
async def nodo_manejar_error(state: AgentState) -> AgentState:
    intentos = state.get("intentos", 0) + 1
    if intentos < 2:
        # reintento simple: vuelve a intentar la ruta original una vez
        return {"intentos": intentos, "error": None}
    return {
        "intentos": intentos,
        "respuesta": "Ocurrió un problema técnico al procesar tu solicitud. Por favor intenta de nuevo en unos momentos.",
        "citas": [],
    }


# ---------- Enrutamiento condicional ----------
def _decidir_ruta_inicial(state: AgentState) -> str:
    return state["ruta"]


def _decidir_tras_rag(state: AgentState) -> str:
    return "error" if state.get("error") else "validar"


def _decidir_tras_validar(state: AgentState) -> str:
    return "generar" if state.get("evidencia_suficiente") else "sin_informacion"


def _decidir_tras_tool(state: AgentState) -> str:
    return "error" if state.get("error") else "generar"


def _decidir_tras_error(state: AgentState) -> str:
    if state.get("respuesta"):  # ya se rindió tras 2 intentos
        return "fin"
    return state["ruta"]  # reintenta la ruta original


def construir_grafo():
    graph = StateGraph(AgentState)

    graph.add_node("clasificar", nodo_clasificar)
    graph.add_node("rag", nodo_rag)
    graph.add_node("tool", nodo_tool)
    graph.add_node("validar_evidencia", nodo_validar_evidencia)
    graph.add_node("generar_rag", nodo_generar_rag)
    graph.add_node("generar_tool", nodo_generar_tool)
    graph.add_node("generar_directo", nodo_generar_directo)
    graph.add_node("sin_informacion", nodo_sin_informacion)
    graph.add_node("manejar_error", nodo_manejar_error)

    graph.set_entry_point("clasificar")

    graph.add_conditional_edges(
        "clasificar", _decidir_ruta_inicial, {"rag": "rag", "tool": "tool", "directo": "generar_directo"}
    )

    graph.add_conditional_edges("rag", _decidir_tras_rag, {"error": "manejar_error", "validar": "validar_evidencia"})
    graph.add_conditional_edges(
        "validar_evidencia", _decidir_tras_validar, {"generar": "generar_rag", "sin_informacion": "sin_informacion"}
    )
    graph.add_conditional_edges("tool", _decidir_tras_tool, {"error": "manejar_error", "generar": "generar_tool"})

    graph.add_conditional_edges(
        "manejar_error", _decidir_tras_error, {"rag": "rag", "tool": "tool", "fin": END}
    )

    graph.add_edge("generar_rag", END)
    graph.add_edge("generar_tool", END)
    graph.add_edge("generar_directo", END)
    graph.add_edge("sin_informacion", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = construir_grafo()
    return _compiled_graph
