import { PublicClientApplication } from '@azure/msal-browser';

const configuredClientId = (import.meta.env.VITE_ENTRA_CLIENT_ID || '').trim();
export const entraApiScope = (import.meta.env.VITE_ENTRA_API_SCOPE || '').trim();
export const entraConfigured = Boolean(configuredClientId && entraApiScope);

export const msalConfig = {
  auth: {
    // The placeholder lets the login screen render before the public Entra IDs
    // are configured. Sign-in remains disabled while entraConfigured is false.
    clientId: configuredClientId || '00000000-0000-0000-0000-000000000000',
    authority: import.meta.env.VITE_ENTRA_AUTHORITY || 'https://login.microsoftonline.com/common',
    redirectUri: import.meta.env.VITE_ENTRA_REDIRECT_URI
      || new URL('/auth-redirect.html', window.location.origin).href,
    postLogoutRedirectUri: window.location.origin,
    navigateToLoginRequestUrl: true,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    allowNativeBroker: false,
    popupBridgeTimeout: 20_000,
  },
};

export const loginRequest = {
  scopes: ['openid', 'profile', 'email', entraApiScope].filter(Boolean),
  prompt: 'select_account',
};

export const msalInstance = new PublicClientApplication(msalConfig);
