import { API_CONFIG } from '../constants/config';

/**
 * Fetches alerts from the API
 * @returns {Promise<Array>} Array of alerts
 */
export const fetchAlerts = async () => {
  try {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.ALERTS}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data.alerts || [];
  } catch (error) {
    console.error('Error loading alerts:', error);
    throw error;
  }
};

/**
 * Starts a workflow for a given alert
 * @param {Object} alert - The alert object
 * @returns {Promise<Object>} Response data
 */
export const startWorkflow = async (alert) => {
  try {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.WORKFLOW_START}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(alert),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error starting workflow:', error);
    throw error;
  }
};

/**
 * Submits an analyst decision
 * @param {Object} decision - The decision object
 * @returns {Promise<Object>} Response data
 */
export const submitDecision = async (decision) => {
  try {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.WORKFLOW_DECISION}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(decision),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error submitting decision:', error);
    throw error;
  }
};
