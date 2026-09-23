"""
Herramienta SQL controlada.

Principio de seguridad del reto: el modelo NUNCA genera ni envía SQL libre.
Solo puede invocar operaciones tipadas y predefinidas (consultar_tabla), con:
  - Whitelist de tablas permitidas (config.allowed_tables)
  - Whitelist de columnas de filtro por tabla
  - Parametrización real vía pyodbc (placeholders ?), nunca f-strings/concat
  - Timeout duro por consulta
  - Límite duro de filas devueltas
"""
import asyncio
from typing import Any

import pyodbc
from fastapi import HTTPException

from config import get_settings

settings = get_settings()

# Whitelist de columnas de filtro válidas por tabla (evita inyección incluso en nombres de columna)
ALLOWED_FILTER_COLUMNS: dict[str, set[str]] = {
    "productos": {"id", "categoria", "nombre", "activo"},
    "pedidos": {"id", "cliente_id", "estado", "fecha"},
    "clientes": {"id", "email", "activo"},
    "inventario": {"producto_id", "almacen_id"},
}


def _get_connection() -> pyodbc.Connection:
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER=tcp:{settings.sql_server},1433;"
        f"DATABASE={settings.sql_database};"
        f"UID={settings.sql_user};PWD={settings.sql_password};"
        f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=5;"
    )
    return pyodbc.connect(conn_str, timeout=settings.query_timeout_seconds)


def _run_query_sync(tabla: str, filtros: dict[str, Any]) -> list[dict]:
    if tabla not in settings.allowed_tables:
        raise HTTPException(status_code=400, detail=f"Tabla '{tabla}' no está autorizada.")

    columnas_validas = ALLOWED_FILTER_COLUMNS.get(tabla, set())
    for col in filtros:
        if col not in columnas_validas:
            raise HTTPException(
                status_code=400,
                detail=f"Columna de filtro '{col}' no permitida para la tabla '{tabla}'.",
            )

    # Construcción segura: nombres de tabla/columna vienen SOLO de la whitelist (nunca del input),
    # los VALORES siempre van parametrizados con placeholders `?`.
    where_clause = ""
    params: list[Any] = []
    if filtros:
        conditions = [f"{col} = ?" for col in filtros]
        where_clause = "WHERE " + " AND ".join(conditions)
        params = list(filtros.values())

    query = f"SELECT TOP {settings.max_rows_returned} * FROM {tabla} {where_clause}"

    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


async def consultar_tabla(tabla: str, filtros: dict[str, Any]) -> list[dict]:
    """Ejecuta la consulta en un thread aparte (pyodbc es bloqueante) con timeout duro."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_run_query_sync, tabla, filtros),
            timeout=settings.query_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="La consulta SQL excedió el tiempo límite.") from exc
    except pyodbc.Error as exc:
        raise HTTPException(status_code=502, detail=f"Error de base de datos: {exc}") from exc
