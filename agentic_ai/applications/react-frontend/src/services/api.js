import { BACKEND_URL } from '../constants/index.js';
import { buildAuthHeaders } from '../utils/helpers.jsx';

/**
 * API Service for backend communication
 */

/**
 * Fetch authentication configuration from backend
 * @returns {Promise<object>} Auth configuration
 */
export const fetchAuthConfig = async () => {
  const response = await fetch(`${BACKEND_URL}/auth/config`);
  return response.json();
};

/**
 * Fetch available agents from backend
 * @param {string} accessToken - Optional access token for authentication
 * @returns {Promise<object>} Agents data
 */
export const fetchAgents = async (accessToken = null) => {
  const response = await fetch(`${BACKEND_URL}/agents`, {
    headers: {
      ...buildAuthHeaders(accessToken),
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch agents: ${response.status}`);
  }

  return response.json();
};

/**
 * Set the active agent
 * @param {string} modulePath - The module path of the agent to activate
 * @param {string} accessToken - Optional access token for authentication
 * @returns {Promise<object>} Result of the operation
 */
export const setActiveAgent = async (modulePath, accessToken = null) => {
  const response = await fetch(`${BACKEND_URL}/agents/set`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...buildAuthHeaders(accessToken),
    },
    body: JSON.stringify({ module_path: modulePath }),
  });

  return response.json();
};

/**
 * Reset a session
 * @param {string} sessionId - The session ID to reset
 * @param {string} accessToken - Optional access token for authentication
 * @returns {Promise<void>}
 */
export const resetSession = async (sessionId, accessToken = null) => {
  await fetch(`${BACKEND_URL}/reset_session`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...buildAuthHeaders(accessToken),
    },
    body: JSON.stringify({ session_id: sessionId }),
  });
};
