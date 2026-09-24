"""
Endpoints de documentos: genera una URL SAS temporal (el frontend sube directo
a Blob Storage con esa URL, sin pasar el archivo por el backend), y dispara la
ingesta en el worker una vez que el frontend confirma que la subida terminó.
Además: listar y eliminar documentos del usuario.
"""
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from azure.identity import DefaultAzureCredential
from fastapi import APIRouter, Depends, HTTPException

from auth import verify_user_token
from config import get_settings

settings = get_settings()
router = APIRouter(prefix="/documentos", tags=["documentos"])

# El account key no se usa directo (Workload Identity no expone key) — se usa
# un User Delegation Key, obtenido con la propia identidad del backend.
from azure.storage.blob import BlobServiceClient  # noqa: E402


def _blob_service_client() -> BlobServiceClient:
    account_url = f"https://{settings.storage_account_name}.blob.core.windows.net"
    return BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())


@router.post("/upload-url")
async def generar_url_subida(nombre_archivo: str, claims: dict = Depends(verify_user_token)):
    user_id = claims.get("oid") or claims.get("sub")
    extension = nombre_archivo.split(".")[-1].lower()
    if extension not in ("pdf", "docx", "txt"):
        raise HTTPException(status_code=400, detail="Solo se permiten PDF, DOCX o TXT.")

    blob_name = f"{user_id}/{uuid.uuid4()}-{nombre_archivo}"

    service_client = _blob_service_client()
    start = datetime.now(timezone.utc) - timedelta(minutes=5)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
    user_delegation_key = service_client.get_user_delegation_key(start, expiry)

    sas_token = generate_blob_sas(
        account_name=settings.storage_account_name,
        container_name="documentos",
        blob_name=blob_name,
        user_delegation_key=user_delegation_key,
        permission=BlobSasPermissions(write=True, create=True),
        expiry=expiry,
        start=start,
    )

    upload_url = (
        f"https://{settings.storage_account_name}.blob.core.windows.net/documentos/{blob_name}?{sas_token}"
    )
    return {"upload_url": upload_url, "blob_name": blob_name}


@router.post("/confirmar-subida")
async def confirmar_subida(blob_name: str, claims: dict = Depends(verify_user_token)):
    """El frontend llama esto tras subir con éxito a la SAS URL — dispara la ingesta en el worker."""
    user_id = claims.get("oid") or claims.get("sub")
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(
                f"{settings.worker_url}/ingest",
                json={"blob_name": blob_name, "owner": user_id},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Error al procesar el documento: {exc.response.text}",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Error al procesar el documento: {exc}") from exc
    return response.json()
