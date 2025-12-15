import React from 'react';
import { Alert, Snackbar } from '@mui/material';
import { useNotification } from '../contexts/NotificationContext.jsx';

/**
 * GlobalNotification component
 * Displays global notifications using Material UI Snackbar
 * Connected to NotificationContext for app-wide access
 */
export const GlobalNotification = () => {
  const { notification, closeNotification } = useNotification();

  return (
    <Snackbar
      open={notification.open}
      autoHideDuration={notification.autoHideDuration}
      onClose={closeNotification}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
    >
      <Alert
        onClose={closeNotification}
        severity={notification.severity}
        variant="filled"
        elevation={6}
        sx={{ width: '100%' }}
      >
        {notification.message}
      </Alert>
    </Snackbar>
  );
};
