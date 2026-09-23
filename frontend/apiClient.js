/**
 * Cliente hacia el backend/orquestador. Siempre adjunta el access token del
 * usuario (obtenido vía MSAL) — el backend valida ese JWT en cada request.
 */
export function createApiClient(backendUrl, getAccessToken) {
  async function request(path, options = {}) {
    const token = await getAccessToken();
    const response = await fetch(`${backendUrl}${path}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      const detail = await response.text().catch(() => "");
      throw new Error(`Error ${response.status}: ${detail || response.statusText}`);
    }
    return response.json();
  }

  return {
    chat: (conversationId, mensaje) =>
      request("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: conversationId, mensaje }),
      }),

    solicitarUrlSubida: (nombreArchivo) =>
      request(`/documentos/upload-url?nombre_archivo=${encodeURIComponent(nombreArchivo)}`, {
        method: "POST",
      }),

    confirmarSubida: (blobName) =>
      request(`/documentos/confirmar-subida?blob_name=${encodeURIComponent(blobName)}`, {
        method: "POST",
      }),
  };
}

/** Sube el archivo directo a Blob Storage usando la SAS URL (no pasa por el backend). */
export async function subirArchivoConSas(uploadUrl, archivo) {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "x-ms-blob-type": "BlockBlob",
      "Content-Type": archivo.type || "application/octet-stream",
    },
    body: archivo,
  });
  if (!response.ok) {
    throw new Error(`Falló la subida directa a Storage: ${response.status}`);
  }
}
