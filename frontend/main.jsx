import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { loadRuntimeConfig } from "./runtimeConfig";

async function bootstrap() {
  const config = await loadRuntimeConfig();
  createRoot(document.getElementById("root")).render(
    <StrictMode>
      <App config={config} />
    </StrictMode>
  );
}

bootstrap().catch((err) => {
  document.getElementById("root").innerHTML =
    `<div style="padding:2rem;font-family:sans-serif;color:#dc2626">Error al iniciar: ${err.message}</div>`;
});
