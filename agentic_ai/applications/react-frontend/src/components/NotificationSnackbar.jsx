import React from 'react';
import { Alert, Snackbar } from '@mui/material';

/**
 * NotificationSnackbar component - Displays notification messages
 * @param {object} props
 * @param {boolean} props.open - Whether snackbar is open
 * @param {string} props.message - Message to display
 * @param {string} props.severity - Severity level (success, error, warning, info)
 * @param {function} props.onClose - Close handler
 */
export const NotificationSnackbar = ({ open, message, severity, onClose }) => {
  return (
    <Snackbar
      open={open}
      autoHideDuration={4000}
      onClose={onClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
    >
      <Alert
        onClose={onClose}
        severity={severity}
        sx={{ width: '100%' }}
      >
        {message}
      </Alert>
    </Snackbar>
  );
};
