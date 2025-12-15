/**
 * Resolves the backend URL from environment variables or current location
 * @returns {string} The backend URL
 */
export const resolveBackendUrl = () => {
  if (import.meta.env.VITE_BACKEND_URL) {
    return import.meta.env.VITE_BACKEND_URL;
  }
  if (typeof window !== 'undefined') {
    if (window.location.hostname === 'localhost') {
      return 'http://localhost:7000';
    }
    return window.location.origin;
  }
  return 'http://localhost:7000';
};

export const BACKEND_URL = resolveBackendUrl();
export const WS_URL = BACKEND_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/chat';

/**
 * WebSocket reconnection delay in milliseconds
 */
export const WS_RECONNECT_DELAY = 3000;
