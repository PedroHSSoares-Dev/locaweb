const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/$/, '');

async function request(token, path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      typeof body.detail === 'string' ? body.detail : `Falha HTTP ${response.status}`,
    );
    error.status = response.status;
    throw error;
  }
  return body;
}

export function listOperationalAlerts(token, filters = {}, signal) {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.priority) params.set('priority', filters.priority);
  const suffix = params.size ? `?${params}` : '';
  return request(token, `/operations/alerts${suffix}`, { signal });
}

export function getOperationalModelSources(token, signal) {
  return request(token, '/models/registry', { signal });
}

export function createOperationalAlert(token, payload) {
  return request(token, '/operations/alerts', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateOperationalAlert(token, alertId, payload) {
  return request(token, `/operations/alerts/${encodeURIComponent(alertId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}
