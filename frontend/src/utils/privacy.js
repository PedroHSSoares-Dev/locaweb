const STREAMER_MODE_EVENT = 'predictfy:streamer-mode-change';

export function streamerModeStorageKey(email = '') {
  const identity = String(email).trim().toLowerCase() || 'anonymous';
  return `predictfy_streamer_mode:${identity}`;
}

export function readStreamerMode(email) {
  try {
    return window.localStorage.getItem(streamerModeStorageKey(email)) === 'true';
  } catch {
    return false;
  }
}

export function writeStreamerMode(email, enabled) {
  const detail = { email: String(email).trim().toLowerCase(), enabled: Boolean(enabled) };
  try {
    window.localStorage.setItem(streamerModeStorageKey(email), String(detail.enabled));
  } catch {
    // The preference remains active for the current view when storage is unavailable.
  }
  window.dispatchEvent(new CustomEvent(STREAMER_MODE_EVENT, { detail }));
}

export function subscribeToStreamerMode(email, callback) {
  const normalizedEmail = String(email).trim().toLowerCase();
  const onPreferenceChange = (event) => {
    if (event.detail?.email === normalizedEmail) callback(event.detail.enabled);
  };
  const onStorageChange = (event) => {
    if (event.key === streamerModeStorageKey(email)) callback(event.newValue === 'true');
  };

  window.addEventListener(STREAMER_MODE_EVENT, onPreferenceChange);
  window.addEventListener('storage', onStorageChange);
  return () => {
    window.removeEventListener(STREAMER_MODE_EVENT, onPreferenceChange);
    window.removeEventListener('storage', onStorageChange);
  };
}

export function protectedIdentity(value) {
  const normalized = String(value || '').trim().toLowerCase();
  if (!normalized) return 'IDENTIDADE PROTEGIDA';

  let hash = 2166136261;
  for (let index = 0; index < normalized.length; index += 1) {
    hash ^= normalized.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  return `IDENTIDADE #${String((hash >>> 0) % 10_000).padStart(4, '0')}`;
}

