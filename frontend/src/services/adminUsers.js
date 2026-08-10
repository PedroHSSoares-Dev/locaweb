import { API_BASE } from '../auth/auth-context';

function readableDetail(detail) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.message || String(item))
      .filter(Boolean)
      .join(' ');
  }
  if (detail && typeof detail === 'object') {
    return detail.message || detail.error || JSON.stringify(detail);
  }
  return '';
}

async function adminRequest(path, token, options = {}) {
  const sendsMutation = options.method && options.method !== 'GET';
  const response = await fetch(`${API_BASE}/admin/users${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(sendsMutation ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      readableDetail(data.detail) || data.message || `Falha na operação (HTTP ${response.status}).`,
    );
    error.status = response.status;
    throw error;
  }
  return data;
}

export function listAdminUsers(token, signal) {
  return adminRequest('', token, { signal }).then((payload) => {
    if (Array.isArray(payload)) return payload;
    return payload.users || payload.items || [];
  });
}

export function createAdminUser(token, input) {
  return adminRequest('', token, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function updateAdminUser(token, userId, input) {
  return adminRequest(`/${encodeURIComponent(userId)}`, token, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export function deleteAdminUser(token, userId, version) {
  const query = version ? `?version=${encodeURIComponent(version)}` : '';
  return adminRequest(`/${encodeURIComponent(userId)}${query}`, token, { method: 'DELETE' });
}
