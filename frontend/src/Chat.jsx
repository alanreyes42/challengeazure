import { useState, useRef, useEffect } from "react";

export default function Chat({ api }) {
  const [conversationId] = useState(() => crypto.randomUUID());
  const [mensajes, setMensajes] = useState([]);
  const [entrada, setEntrada] = useState("");
  const [cargando, setCargando] = useState(false);
  const finRef = useRef(null);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes]);

  async function enviar(e) {
    e.preventDefault();
    const texto = entrada.trim();
    if (!texto || cargando) return;

    setMensajes((m) => [...m, { rol: "usuario", texto }]);
    setEntrada("");
    setCargando(true);

    try {
      const resultado = await api.chat(conversationId, texto);
      setMensajes((m) => [
        ...m,
        { rol: "asistente", texto: resultado.respuesta, citas: resultado.citas, ruta: resultado.ruta_tomada },
      ]);
    } catch (err) {
      setMensajes((m) => [...m, { rol: "asistente", texto: `Ocurrió un error: ${err.message}`, citas: [] }]);
    } finally {
      setCargando(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ flex: 1, overflowY: "auto", padding: "1rem" }}>
        {mensajes.map((m, i) => (
          <div key={i} style={{ marginBottom: "1rem", textAlign: m.rol === "usuario" ? "right" : "left" }}>
            <div
              style={{
                display: "inline-block",
                maxWidth: "70%",
                padding: "0.75rem 1rem",
                borderRadius: "0.75rem",
                background: m.rol === "usuario" ? "#2563eb" : "#f1f5f9",
                color: m.rol === "usuario" ? "#fff" : "#0f172a",
                whiteSpace: "pre-wrap",
              }}
            >
              {m.texto}
            </div>
            {m.citas && m.citas.length > 0 && (
              <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "#64748b" }}>
                {m.citas.map((c, j) => (
                  <div key={j}>
                    📄 {c.document_id} — página {c.pagina}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {cargando && <div style={{ color: "#64748b" }}>Pensando…</div>}
        <div ref={finRef} />
      </div>
      <form onSubmit={enviar} style={{ display: "flex", gap: "0.5rem", padding: "1rem", borderTop: "1px solid #e2e8f0" }}>
        <input
          value={entrada}
          onChange={(e) => setEntrada(e.target.value)}
          placeholder="Escribe tu pregunta aquí..."
          style={{ flex: 1, padding: "0.75rem", borderRadius: "0.5rem", border: "1px solid #cbd5e1" }}
        />
        <button
          type="submit"
          disabled={cargando}
          style={{ padding: "0.75rem 1.25rem", borderRadius: "0.5rem", background: "#2563eb", color: "#fff", border: "none" }}
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
