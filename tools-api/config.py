"""
Configuración central de la API de Herramientas.
Todos los secretos se leen de variables de entorno (inyectadas por Key Vault vía
Workload Identity en AKS, o CSI Secret Store), NUNCA hardcodeados.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Identidad / seguridad ---
    # Client ID de la app registrada en Entra ID (para validar el JWT del backend)
    entra_tenant_id: str = os.getenv("ENTRA_TENANT_ID", "")
    entra_audience: str = os.getenv("ENTRA_AUDIENCE", "")  # api://<AppId>

    # --- SQL (Azure SQL Database) ---
    sql_server: str = os.getenv("SQL_SERVER", "")          # docuassist-sql-dev-03.database.windows.net
    sql_database: str = os.getenv("SQL_DATABASE", "db-negocio")
    sql_user: str = os.getenv("SQL_USER", "")
    sql_password: str = os.getenv("SQL_PASSWORD", "")       # viene de Key Vault, no de aquí en texto plano

    # --- Cosmos DB ---
    cosmos_endpoint: str = os.getenv("COSMOS_ENDPOINT", "")
    cosmos_key: str = os.getenv("COSMOS_KEY", "")
    cosmos_database: str = os.getenv("COSMOS_DATABASE", "AgentState")
    cosmos_container: str = os.getenv("COSMOS_CONTAINER", "Conversaciones")

    # --- Límites de seguridad (controles anti-abuso del reto) ---
    query_timeout_seconds: int = int(os.getenv("QUERY_TIMEOUT_SECONDS", "5"))
    max_rows_returned: int = int(os.getenv("MAX_ROWS_RETURNED", "50"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

    # --- Tablas/columnas permitidas (whitelist, nunca SQL libre) ---
    allowed_tables: list[str] = ["productos", "pedidos", "clientes", "inventario"]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
