"""
Lectura y validación de documentos en Blob Storage.
Solo alcanzable desde dentro de la VNet (el Storage tiene Private Endpoint) —
el worker corre en AKS, dentro de la misma red, así que no necesita acceso público.
"""
import os

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from fastapi import HTTPException

from config import get_settings

settings = get_settings()


async def _get_blob_client():
    account_url = f"https://{settings.storage_account_name}.blob.core.windows.net"
    credential = DefaultAzureCredential()  # usa la Workload Identity del pod
    return BlobServiceClient(account_url=account_url, credential=credential)


async def validar_y_descargar(blob_name: str) -> bytes:
    """Valida extensión y tamaño, y descarga el archivo. Lanza HTTPException si no cumple."""
    ext = os.path.splitext(blob_name)[1].lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión '{ext}' no permitida. Solo: {settings.allowed_extensions}",
        )

    async with await _get_blob_client() as service_client:
        container_client = service_client.get_container_client(settings.storage_container)
        blob_client = container_client.get_blob_client(blob_name)

        try:
            properties = await blob_client.get_blob_properties()
        except Exception as exc:
            raise HTTPException(status_code=404, detail=f"Blob '{blob_name}' no encontrado.") from exc

        size_mb = properties.size / (1024 * 1024)
        if size_mb > settings.max_file_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo de {size_mb:.1f} MB excede el límite de {settings.max_file_size_mb} MB.",
            )

        stream = await blob_client.download_blob()
        return await stream.readall()
