import { useState } from "react";
import { subirArchivoConSas } from "./apiClient";

export default function DocumentUpload({ api }) {
  const [estado, setEstado] = useState("idle"); // idle | subiendo | procesando | listo | error
  const [mensaje, setMensaje] = useState("");

  async function manejarArchivo(e) {
    const archivo = e.target.files?.[0];
    if (!archivo) return;

    try {
      setEstado("subiendo");
      setMensaje(`Subiendo ${archivo.name}...`);

      const { upload_url, blob_name } = await api.solicitarUrlSubida(archivo.name);
      await subirArchivoConSas(upload_url, archivo);

      setEstado("procesando");
      setMensaje("Documento subido. Extrayendo e indexando contenido...");

      const resultado = await api.confirmarSubida(blob_name);

      setEstado("listo");
      setMensaje(`Listo: ${resultado.chunks_indexados} fragmentos indexados de ${resultado.paginas} página(s).`);
    } catch (err) {
      setEstado("error");
      setMensaje(`Error: ${err.message}`);
    }
  }

  return (
    <div style={{ padding: "1rem", borderBottom: "1px solid #e2e8f0" }}>
      <label style={{ display: "inline-block", cursor: "pointer", color: "#2563eb", fontWeight: 600 }}>
        📎 Subir documento (PDF, DOCX o TXT)
        <input type="file" accept=".pdf,.docx,.txt" onChange={manejarArchivo} style={{ display: "none" }} />
      </label>
      {mensaje && (
        <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: estado === "error" ? "#dc2626" : "#475569" }}>
          {mensaje}
        </div>
      )}
    </div>
  );
}
