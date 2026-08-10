import { useContext } from 'react';
import { API_BASE, AuthContext } from '../auth/auth-context';

export const CHAT_API_BASE = API_BASE;

// Compatibility alias: authentication now protects the complete application.
export function useChatAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useChatAuth deve ser usado dentro de AuthProvider.');
  return context;
}
