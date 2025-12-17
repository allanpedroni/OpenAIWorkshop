import React, { Component } from 'react';
import { Box, Paper, Typography, Button, Alert } from '@mui/material';
import { Error as ErrorIcon, Refresh as RefreshIcon } from '@mui/icons-material';

/**
 * ErrorBoundary Component
 * Catches React errors and displays a user-friendly error page
 * Prevents the entire app from crashing due to component errors
 */
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console for debugging
    console.error('Error caught by ErrorBoundary:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });

    // You could also log to an error reporting service here
    // e.g., Sentry, LogRocket, Application Insights, etc.
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'background.default',
            p: 3,
          }}
        >
          <Paper
            elevation={6}
            sx={{
              p: 4,
              maxWidth: 600,
              width: '100%',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
              <ErrorIcon color="error" sx={{ fontSize: 48 }} />
              <Box>
                <Typography variant="h5" gutterBottom>
                  Oops! Something went wrong
                </Typography>
                <Typography color="text.secondary">
                  The application encountered an unexpected error.
                </Typography>
              </Box>
            </Box>

            {this.state.error && (
              <Alert severity="error" sx={{ mb: 3 }}>
                <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                  {this.state.error.toString()}
                </Typography>
              </Alert>
            )}

            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Button
                variant="contained"
                startIcon={<RefreshIcon />}
                onClick={this.handleReload}
              >
                Reload Page
              </Button>
              <Button
                variant="outlined"
                onClick={this.handleReset}
              >
                Try Again
              </Button>
            </Box>

            {import.meta.env.DEV && this.state.errorInfo && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                  Error Details (Development Only):
                </Typography>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    bgcolor: 'grey.50',
                    maxHeight: 200,
                    overflow: 'auto',
                  }}
                >
                  <Typography
                    variant="caption"
                    component="pre"
                    sx={{
                      fontFamily: 'monospace',
                      fontSize: '0.7rem',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {this.state.errorInfo.componentStack}
                  </Typography>
                </Paper>
              </Box>
            )}

            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 3 }}>
              If this problem persists, please contact support with the error details above.
            </Typography>
          </Paper>
        </Box>
      );
    }

    return this.props.children;
  }
}
