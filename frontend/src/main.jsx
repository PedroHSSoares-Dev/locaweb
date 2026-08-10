import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MsalProvider } from '@azure/msal-react'
import './index.css'
import App from './App.jsx'
import { msalInstance } from './auth/entra.js'
import { AuthProvider } from './context/AuthContext.jsx'

function canonicalLocalUrl() {
  const redirectUri = import.meta.env.VITE_ENTRA_REDIRECT_URI;
  if (!import.meta.env.DEV || !redirectUri) return null;
  try {
    const configured = new URL(redirectUri);
    const current = new URL(window.location.href);
    const localHosts = new Set(['localhost', '127.0.0.1']);
    if (
      configured.origin !== current.origin
      && localHosts.has(configured.hostname)
      && localHosts.has(current.hostname)
    ) {
      current.protocol = configured.protocol;
      current.hostname = configured.hostname;
      current.port = configured.port;
      return current.href;
    }
  } catch {
    // A configuração inválida será apresentada pelo gate de autenticação.
  }
  return null;
}

const canonicalUrl = canonicalLocalUrl();
if (canonicalUrl) {
  window.location.replace(canonicalUrl);
} else {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <MsalProvider instance={msalInstance}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MsalProvider>
    </StrictMode>,
  );
}
