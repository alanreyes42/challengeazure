import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Storage ---
    storage_account_name: str = os.getenv("STORAGE_ACCOUNT_NAME", "")
    storage_container: str = os.getenv("STORAGE_CONTAINER", "documentos")

    # --- Document Intelligence ---
    docintel_endpoint: str = os.getenv("DOCINTEL_ENDPOINT", "")
    docintel_key: str = os.getenv("DOCINTEL_KEY", "")

    # --- Azure AI Foundry (embeddings) ---
    foundry_endpoint: str = os.getenv("FOUNDRY_ENDPOINT", "")
    foundry_key: str = os.getenv("FOUNDRY_KEY", "")
    embeddings_deployment: str = os.getenv("EMBEDDINGS_DEPLOYMENT", "embeddings-model")

    # --- Azure AI Search ---
    search_endpoint: str = os.getenv("SEARCH_ENDPOINT", "")
    search_key: str = os.getenv("SEARCH_KEY", "")
    search_index_name: str = os.getenv("SEARCH_INDEX_NAME", "documentos-index")

    # --- Validación de archivos ---
    allowed_extensions: list[str] = [".pdf", ".docx", ".txt"]
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "25"))

    # --- Chunking ---
    chunk_size_tokens: int = int(os.getenv("CHUNK_SIZE_TOKENS", "500"))
    chunk_overlap_tokens: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "50"))

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
