import { useState, useEffect } from 'react';
import { useChatAuth } from './useChatAuth';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';

/**
 * Hook genérico para consumir a API Predictfy.
 * @param {string} endpoint  Ex.: '/previsoes/d1', '/risco/produtos', '/context'
 * @param {object} params    Query params opcionais. Ex.: { periodo: 'trimestre' }
 * @returns {{ data, loading, error, disponivel }}
 *   - disponivel: false quando data.disponivel === false OU quando fetch falha
 */
export function useApi(endpoint, params = {}) {
  const { user, logout } = useChatAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [disponivel, setDisponivel] = useState(false);

  const query = Object.keys(params).length
    ? '?' + new URLSearchParams(params).toString()
    : '';

  useEffect(() => {
    let cancelled = false;

    queueMicrotask(() => {
      if (cancelled) return;
      setLoading(true);
      setError(false);
      setData(null);
      setDisponivel(false);
    });

    fetch(`${BASE_URL}${endpoint}${query}`, {
      headers: { Authorization: `Bearer ${user.token}` },
    })
      .then(res => {
        if (res.status === 401) logout();
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(json => {
        if (cancelled) return;
        setData(json);
        setDisponivel(json?.disponivel !== false);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setError(true);
        setDisponivel(false);
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, [endpoint, query, logout, user.token]);

  return { data, loading, error, disponivel };
}
