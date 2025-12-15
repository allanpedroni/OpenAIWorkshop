/**
 * UI helper functions for components
 */

/**
 * Gets the appropriate icon for alert severity
 * @param {string} severity - Alert severity level
 * @param {Object} icons - Icon components object
 * @returns {JSX.Element} Icon component
 */
export const getSeverityIcon = (severity, icons) => {
  const { ErrorIcon, WarningIcon, InfoIcon } = icons;
  switch (severity) {
    case 'high':
      return <ErrorIcon color="error" />;
    case 'medium':
      return <WarningIcon color="warning" />;
    case 'low':
      return <InfoIcon color="info" />;
    default:
      return <InfoIcon />;
  }
};

/**
 * Gets the appropriate color for alert severity
 * @param {string} severity - Alert severity level
 * @returns {string} MUI color name
 */
export const getSeverityColor = (severity) => {
  switch (severity) {
    case 'high':
      return 'error';
    case 'medium':
      return 'warning';
    case 'low':
      return 'info';
    default:
      return 'default';
  }
};

/**
 * Gets the appropriate icon for event type
 * @param {Object} event - Event object
 * @param {Object} icons - Icon components object
 * @returns {JSX.Element} Icon component
 */
export const getEventIcon = (event, icons) => {
  const { PlayArrowIcon, CheckCircleIcon, InfoIcon, GavelIcon, ErrorIcon } = icons;
  
  switch (event.event_type) {
    case 'executor_invoked':
      return <PlayArrowIcon color="primary" />;
    case 'executor_completed':
      return <CheckCircleIcon color="success" />;
    case 'status_change':
      return <InfoIcon color="info" />;
    case 'workflow_output':
      return <CheckCircleIcon color="success" />;
    default:
      if (event.type === 'decision_required') {
        return <GavelIcon color="warning" />;
      }
      if (event.type === 'workflow_error') {
        return <ErrorIcon color="error" />;
      }
      return <InfoIcon />;
  }
};

/**
 * Gets the appropriate color for event type
 * @param {Object} event - Event object
 * @returns {string} MUI color name
 */
export const getEventColor = (event) => {
  switch (event.event_type) {
    case 'executor_invoked':
      return 'primary';
    case 'executor_completed':
      return 'success';
    case 'status_change':
      return 'info';
    case 'workflow_output':
      return 'success';
    default:
      if (event.type === 'decision_required') {
        return 'warning';
      }
      if (event.type === 'workflow_error') {
        return 'error';
      }
      return 'default';
  }
};

/**
 * Gets the display title for an event
 * @param {Object} event - Event object
 * @returns {string} Event title
 */
export const getEventTitle = (event) => {
  if (event.event_type === 'executor_invoked') {
    return `${event.executor_id} started`;
  }
  if (event.event_type === 'executor_completed') {
    return `${event.executor_id} completed`;
  }
  if (event.event_type === 'status_change') {
    return `Status: ${event.status}`;
  }
  if (event.event_type === 'workflow_output') {
    return 'Workflow Output';
  }
  if (event.type === 'decision_required') {
    return 'Decision Required';
  }
  if (event.type === 'workflow_started') {
    return 'Workflow Started';
  }
  if (event.type === 'workflow_completed') {
    return 'Workflow Completed';
  }
  if (event.type === 'workflow_error') {
    return 'Error Occurred';
  }
  return event.type || 'Event';
};

/**
 * Gets risk level from risk score
 * @param {number} score - Risk score (0-1)
 * @returns {string} Risk level
 */
export const getRiskLevel = (score) => {
  if (score >= 0.8) return 'Critical';
  if (score >= 0.6) return 'High';
  if (score >= 0.3) return 'Medium';
  return 'Low';
};

/**
 * Gets risk color from risk score
 * @param {number} score - Risk score (0-1)
 * @returns {string} MUI color name
 */
export const getRiskColor = (score) => {
  if (score >= 0.8) return 'error';
  if (score >= 0.6) return 'warning';
  if (score >= 0.3) return 'info';
  return 'success';
};

/**
 * Gets node status color configuration
 * @param {string} status - Node status
 * @returns {Object} Color configuration object
 */
export const getNodeStatusColor = (status) => {
  switch (status) {
    case 'running':
      return { bg: '#1976d2', text: '#ffffff' };
    case 'completed':
      return { bg: '#4caf50', text: '#ffffff' };
    case 'error':
      return { bg: '#f44336', text: '#ffffff' };
    default:
      return { bg: '#ffffff', text: '#000000' };
  }
};

/**
 * Gets status label for display
 * @param {string} status - Status value
 * @returns {string} Display label
 */
export const getStatusLabel = (status) => {
  switch (status) {
    case 'running':
      return 'Running';
    case 'completed':
      return 'Completed';
    case 'error':
      return 'Error';
    default:
      return 'Idle';
  }
};
