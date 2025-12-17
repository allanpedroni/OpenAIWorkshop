import { useState, useEffect } from 'react';
import { fetchAgents, setActiveAgent } from '../services/api.js';

/**
 * Custom hook for managing agent selection
 * @param {boolean} authConfigLoaded - Whether auth config has loaded
 * @param {boolean} isAuthEnabled - Whether authentication is enabled
 * @param {string} accessToken - Access token for authenticated requests
 * @returns {object} Agent state and methods
 */
export const useAgents = (authConfigLoaded, isAuthEnabled, accessToken) => {
  const [availableAgents, setAvailableAgents] = useState([]);
  const [currentAgent, setCurrentAgent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Fetch available agents from backend
   */
  useEffect(() => {
    const loadAgents = async () => {
      if (!authConfigLoaded) {
        return;
      }
      if (isAuthEnabled && !accessToken) {
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const data = await fetchAgents(accessToken);
        const agents = Array.isArray(data.agents) ? data.agents : [];
        setAvailableAgents(agents);
        setCurrentAgent(data.current_agent ?? (agents[0]?.module_path || ''));
        setError(null); // Clear any previous errors
      } catch (err) {
        console.error('Error fetching agents:', err);
        setError(err.message);
        // Set empty agents array so app can still render
        setAvailableAgents([]);
      } finally {
        setLoading(false);
      }
    };

    loadAgents();
  }, [authConfigLoaded, isAuthEnabled, accessToken]);

  /**
   * Change the active agent
   * @param {string} modulePath - Module path of the agent to activate
   * @returns {Promise<boolean>} Success status
   */
  const changeAgent = async (modulePath) => {
    if (isAuthEnabled && !accessToken) {
      throw new Error('Sign in to change agents');
    }

    setLoading(true);
    setError(null);

    try {
      const data = await setActiveAgent(modulePath, accessToken);
      
      if (data.status === 'success') {
        setCurrentAgent(modulePath);
        return true;
      } else {
        throw new Error(data.message || 'Failed to change agent');
      }
    } catch (err) {
      console.error('Error changing agent:', err);
      setError(err.message);
      return false;
    } finally {
      setLoading(false);
    }
  };

  return {
    availableAgents,
    currentAgent,
    loading,
    error,
    changeAgent,
  };
};
