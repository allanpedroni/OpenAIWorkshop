import React, { createContext, useContext, useState, useCallback } from 'react';

/**
 * Notification Context
 * Provides global notification state and methods throughout the application
 */
const NotificationContext = createContext(null);

/**
 * Hook to access notification system
 * @returns {object} Notification methods and state
 */
export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within NotificationProvider');
  }
  return context;
};

/**
 * NotificationProvider Component
 * Wraps the app to provide global notification functionality
 * @param {object} props
 * @param {React.ReactNode} props.children - Child components
 */
export const NotificationProvider = ({ children }) => {
  const [notification, setNotification] = useState({
    open: false,
    message: '',
    severity: 'info',
    autoHideDuration: 6000,
  });

  /**
   * Show a notification
   * @param {string} message - Message to display
   * @param {string} severity - Severity level: 'success', 'error', 'warning', 'info'
   * @param {number} duration - Auto-hide duration in milliseconds
   */
  const showNotification = useCallback((message, severity = 'info', duration = 6000) => {
    setNotification({
      open: true,
      message,
      severity,
      autoHideDuration: duration,
    });
  }, []);

  /**
   * Show success notification
   * @param {string} message - Success message
   */
  const showSuccess = useCallback((message) => {
    showNotification(message, 'success', 4000);
  }, [showNotification]);

  /**
   * Show error notification
   * @param {string} message - Error message
   * @param {number} duration - Duration (default 8000ms for errors)
   */
  const showError = useCallback((message, duration = 8000) => {
    showNotification(message, 'error', duration);
  }, [showNotification]);

  /**
   * Show warning notification
   * @param {string} message - Warning message
   */
  const showWarning = useCallback((message) => {
    showNotification(message, 'warning', 6000);
  }, [showNotification]);

  /**
   * Show info notification
   * @param {string} message - Info message
   */
  const showInfo = useCallback((message) => {
    showNotification(message, 'info', 4000);
  }, [showNotification]);

  /**
   * Close notification
   */
  const closeNotification = useCallback(() => {
    setNotification((prev) => ({ ...prev, open: false }));
  }, []);

  const value = {
    notification,
    showNotification,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    closeNotification,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};
