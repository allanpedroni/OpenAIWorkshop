/**
 * API configuration constants
 */
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001',
  WS_URL: import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws',
  ENDPOINTS: {
    ALERTS: '/api/alerts',
    WORKFLOW_START: '/api/workflow/start',
    WORKFLOW_DECISION: '/api/workflow/decision',
  },
};

/**
 * WebSocket configuration
 */
export const WS_CONFIG = {
  RECONNECT_DELAY: 3000,
  MAX_RECONNECT_ATTEMPTS: 10,
};

/**
 * Application constants
 */
export const APP_CONFIG = {
  TITLE: import.meta.env.VITE_APP_TITLE || 'Fraud Detection Workflow Visualizer',
};

export default {
  API_CONFIG,
  WS_CONFIG,
  APP_CONFIG,
};
