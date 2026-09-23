import { useMemo } from "react";
import { PublicClientApplication, InteractionType } from "@azure/msal-browser";
import {
  MsalProvider,
  useMsal,
  useIsAuthenticated,
  AuthenticatedTemplate,
  UnauthenticatedTemplate,
} from "@azure/msal-react";

import Chat from "./Chat";
import DocumentUpload from "./DocumentUpload";
import { createApiClient } from "./apiClient";

function LoginScreen() {
  const { instance } = useMsal();
  return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center" }}>
        <h1>DocuAssist AI</h1>
        <p style={{ color: "#64748b", marginBottom: "1.5rem" }}>Asistente de Documentación Empresarial</p>
        <button
          onClick={() => instance.loginRedirect({ scopes: ["User.Read"] })}
          style={{ padding: "0.75rem 1.5rem", borderRadius: "0.5rem", background: "#2563eb", color: "#fff", border: "none" }}
        >
          Iniciar sesión con Microsoft
        </button>
      </div>
    </div>
  );
}

function AuthenticatedApp({ config }) {
  const { instance, accounts } = useMsal();

  const getAccessToken = useMemo(
    () => async () => {
      const request = { scopes: [`${config.entraClientId}/.default`], account: accounts[0] };
      try {
        const result = await instance.acquireTokenSilent(request);
        return result.accessToken;
      } catch {
        const result = await instance.acquireTokenPopup(request);
        return result.accessToken;
      }
    },
    [instance, accounts, config]
  );

  const api = useMemo(() => createApiClient(config.backendUrl, getAccessToken), [config, getAccessToken]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <header style={{ padding: "1rem", borderBottom: "1px solid #e2e8f0", display: "flex", justifyContent: "space-between" }}>
        <strong>DocuAssist AI</strong>
        <span>{accounts[0]?.username}</span>
        <button onClick={() => instance.logoutRedirect()} style={{ border: "none", background: "none", color: "#2563eb", cursor: "pointer" }}>
          Cerrar sesión
        </button>
      </header>
      <DocumentUpload api={api} />
      <div style={{ flex: 1, overflow: "hidden" }}>
        <Chat api={api} />
      </div>
    </div>
  );
}

export default function App({ config }) {
  const msalInstance = useMemo(
    () =>
      new PublicClientApplication({
        auth: {
          clientId: config.entraClientId,
          authority: `https://login.microsoftonline.com/${config.entraTenantId}`,
          redirectUri: config.entraRedirectUri,
        },
        cache: { cacheLocation: "sessionStorage" },
      }),
    [config]
  );

  return (
    <MsalProvider instance={msalInstance}>
      <AuthenticatedTemplate>
        <AuthenticatedApp config={config} />
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <LoginScreen />
      </UnauthenticatedTemplate>
    </MsalProvider>
  );
}
