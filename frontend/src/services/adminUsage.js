import { API_BASE } from '../auth/auth-context';

function readableDetail(detail) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item?.msg || String(item)).join(' ');
  if (detail && typeof detail === 'object') return detail.message || detail.error || JSON.stringify(detail);
  return '';
}

export async function getAdminUsage(token, days, signal) {
  const response = await fetch(`${API_BASE}/admin/usage?days=${encodeURIComponent(days)}`, {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      readableDetail(data.detail) || data.message || `Falha na consulta (HTTP ${response.status}).`,
    );
    error.status = response.status;
    throw error;
  }
  return data;
}
