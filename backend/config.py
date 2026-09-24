import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Identidad (validar tokens de usuarios finales via Entra ID) ---
    entra_tenant_id: str = os.getenv("ENTRA_TENANT_ID", "")
    entra_audience: str = os.getenv("ENTRA_AUDIENCE", "")

    # --- Identidad de servicio (para llamar a tools-api con su propio token) ---
    entra_client_id: str = os.getenv("ENTRA_CLIENT_ID", "")       # AppId del backend
    entra_client_secret: str = os.getenv("ENTRA_CLIENT_SECRET", "")

    # --- Azure AI Foundry (modelos) ---
    foundry_endpoint: str = os.getenv("FOUNDRY_ENDPOINT", "")
    foundry_key: str = os.getenv("FOUNDRY_KEY", "")
    gen_model_deployment: str = os.getenv("GEN_MODEL_DEPLOYMENT", "gen-model")
    router_model_deployment: str = os.getenv("ROUTER_MODEL_DEPLOYMENT", "router-model")
    embeddings_deployment: str = os.getenv("EMBEDDINGS_DEPLOYMENT", "embeddings-model")

    # --- Azure AI Search (recuperación RAG) ---
    search_endpoint: str = os.getenv("SEARCH_ENDPOINT", "")
    search_key: str = os.getenv("SEARCH_KEY", "")
    search_index_name: str = os.getenv("SEARCH_INDEX_NAME", "documentos-index")
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "5"))

    # --- Cosmos DB (memoria conversacional) ---
    cosmos_endpoint: str = os.getenv("COSMOS_ENDPOINT", "")
    cosmos_key: str = os.getenv("COSMOS_KEY", "")
    cosmos_database: str = os.getenv("COSMOS_DATABASE", "AgentState")
    cosmos_container: str = os.getenv("COSMOS_CONTAINER", "Conversaciones")

    # --- Tools API (interno, solo alcanzable dentro del clúster) ---
    tools_api_url: str = os.getenv("TOOLS_API_URL", "http://tools-api-svc.tools-api.svc.cluster.local")

    # --- Worker de ingesta (interno) ---
    worker_url: str = os.getenv("WORKER_URL", "http://worker-svc.worker.svc.cluster.local")

    # --- Storage (para generar SAS de subida) ---
    storage_account_name: str = os.getenv("STORAGE_ACCOUNT_NAME", "")

    # --- Umbral de confianza para "no tengo información suficiente" ---
    min_search_score: float = float(os.getenv("MIN_SEARCH_SCORE", "0.55"))

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
