/**
 * Event helpers for workflow event processing
 */

/**
 * Generates a unique key for an event
 * @param {Object} event - The event object
 * @returns {string} Unique event key
 */
export const generateEventKey = (event) => {
  return `${event.timestamp}-${event.type || event.event_type}-${event.executor_id || ''}`;
};

/**
 * Checks if an event is a duplicate in an array of events
 * @param {Object} event - The event to check
 * @param {Array} events - Existing events array
 * @returns {boolean} True if duplicate
 */
export const isDuplicateEvent = (event, events) => {
  const eventKey = generateEventKey(event);
  return events.some((e) => generateEventKey(e) === eventKey);
};

/**
 * Formats a timestamp for display
 * @param {string|number} timestamp - The timestamp
 * @returns {string} Formatted time string
 */
export const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
};

/**
 * Formats a date and time for display
 * @param {string|number} timestamp - The timestamp
 * @returns {string} Formatted datetime string
 */
export const formatDateTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
};

/**
 * Truncates text to a maximum length
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
export const truncateText = (text, maxLength = 100) => {
  if (!text || text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
};
