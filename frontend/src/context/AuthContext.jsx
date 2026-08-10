import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { InteractionStatus } from '@azure/msal-browser';
import { useMsal } from '@azure/msal-react';
import { entraApiScope, entraConfigured, loginRequest } from '../auth/entra';
import { API_BASE, AuthContext } from '../auth/auth-context';

const STORAGE_KEY = 'predictfy_chat_session';
const PENDING_LOGIN_KEY = 'predictfy_entra_login_pending';
function readStoredSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw);
    if (!session.token || !session.email || session.expiresAt * 1000 <= Date.now()) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return session;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function errorMessage(error) {
  const code = error?.errorCode || error?.code;
  if (code === 'user_cancelled' || code === 'popup_window_error') {
    return 'O login Microsoft foi cancelado.';
  }
  if (code === 'redirect_bridge_timeout') {
    return 'O retorno da Microsoft excedeu 20 segundos. Feche o popup, recarregue a página e tente novamente.';
  }
  if (code === 'timed_out') {
    return 'A autenticação Microsoft excedeu o tempo de espera. Recarregue a página e tente novamente.';
  }
  if (code === 'redirect_uri_not_same_origin') {
    return 'A aplicação e o retorno Microsoft estão em endereços locais diferentes. Use http://localhost:5173.';
  }
  if (error?.message?.includes('Email não autorizado')) {
    return 'Esta conta Microsoft não está na lista de permissão.';
  }
  return error?.message || 'Não foi possível validar a conta Microsoft.';
}

export function AuthProvider({ children }) {
  const { instance, accounts, inProgress } = useMsal();
  const initialSession = useMemo(() => readStoredSession(), []);
  const [user, setUser] = useState(initialSession);
  const [status, setStatus] = useState(initialSession ? 'checking' : 'idle');
  const [error, setError] = useState('');
  const exchangeInFlight = useRef(false);

  const clearLocalSession = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
    setStatus('idle');
  }, []);

  useEffect(() => {
    if (!initialSession?.token) return undefined;
    const controller = new AbortController();
    fetch(`${API_BASE}/chat/session`, {
      headers: { Authorization: `Bearer ${initialSession.token}` },
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error('Sessão inválida');
        setStatus('authorized');
      })
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') clearLocalSession();
      });
    return () => controller.abort();
  }, [clearLocalSession, initialSession]);

  const exchangeAccessToken = useCallback(async (accessToken) => {
    const response = await fetch(`${API_BASE}/chat/session`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.allowed) throw new Error(data.detail || 'Email não autorizado.');

    const session = {
      email: data.email,
      token: data.token,
      expiresAt: data.expires_at,
      accessMode: data.access_mode,
      llmStatus: data.llm_status,
      welcome: data.welcome,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    sessionStorage.removeItem(PENDING_LOGIN_KEY);
    setUser(session);
    setStatus('authorized');
  }, []);

  const signIn = useCallback(async () => {
    if (!entraConfigured) {
      setStatus('denied');
      setError('Entra ID ainda não configurado. Preencha VITE_ENTRA_CLIENT_ID e VITE_ENTRA_API_SCOPE.');
      return;
    }
    setStatus('verifying');
    setError('');
    try {
      sessionStorage.setItem(PENDING_LOGIN_KEY, 'true');
      await instance.loginRedirect(loginRequest);
    } catch (requestError) {
      sessionStorage.removeItem(PENDING_LOGIN_KEY);
      setStatus('denied');
      setError(errorMessage(requestError));
    }
  }, [instance]);

  useEffect(() => {
    const loginPending = sessionStorage.getItem(PENDING_LOGIN_KEY) === 'true';
    if (
      !loginPending
      || user
      || inProgress !== InteractionStatus.None
      || exchangeInFlight.current
    ) return;

    const account = instance.getActiveAccount() || accounts[0];
    if (!account) return;

    exchangeInFlight.current = true;
    instance.setActiveAccount(account);
    Promise.resolve()
      .then(() => {
        setStatus('verifying');
        setError('');
        return instance.acquireTokenSilent({ account, scopes: [entraApiScope] });
      })
      .then((result) => exchangeAccessToken(result.accessToken))
      .catch((requestError) => {
        sessionStorage.removeItem(PENDING_LOGIN_KEY);
        setStatus('denied');
        setError(errorMessage(requestError));
      })
      .finally(() => {
        exchangeInFlight.current = false;
      });
  }, [accounts, exchangeAccessToken, inProgress, instance, user]);

  const releaseSession = useCallback(async (signOutMicrosoft) => {
    const token = user?.token;
    const account = instance.getActiveAccount() || instance.getAllAccounts()[0];
    clearLocalSession();
    setError('');

    if (token) {
      fetch(`${API_BASE}/chat/session`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
        keepalive: true,
      }).catch(() => {});
    }

    if (account && signOutMicrosoft) {
      try {
        await instance.logoutRedirect({
          account,
          postLogoutRedirectUri: window.location.origin,
        });
      } catch {
        await instance.clearCache({ account }).catch(() => {});
      }
    } else if (account) {
      await instance.clearCache({ account }).catch(() => {});
    }
  }, [clearLocalSession, instance, user?.token]);

  const logout = useCallback(() => releaseSession(true), [releaseSession]);

  useEffect(() => {
    if (!user?.expiresAt) return undefined;
    const remaining = user.expiresAt * 1000 - Date.now() - 1_000;
    if (remaining <= 0) {
      queueMicrotask(() => releaseSession(false));
      return undefined;
    }
    const timer = window.setTimeout(() => releaseSession(false), remaining);
    return () => window.clearTimeout(timer);
  }, [releaseSession, user?.expiresAt]);

  const value = useMemo(() => ({
    user,
    status,
    error,
    signIn,
    logout,
    entraConfigured,
  }), [error, logout, signIn, status, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
