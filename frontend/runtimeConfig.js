/**
 * Carga la configuración en TIEMPO DE EJECUCIÓN desde /config.json, en vez de
 * incrustarla en el bundle compilado (requisito del reto). Así, la misma
 * imagen Docker / build estático sirve para DEV, QA y PROD — solo cambia el
 * archivo config.json que se monta o se sirve junto al resto de assets.
 */
let cachedConfig = null;

export async function loadRuntimeConfig() {
  if (cachedConfig) return cachedConfig;
  const response = await fetch("/config.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("No se pudo cargar la configuración runtime (config.json).");
  }
  cachedConfig = await response.json();
  return cachedConfig;
}
