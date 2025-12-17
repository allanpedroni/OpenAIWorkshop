import React from 'react';
import { Box, Paper, Typography, LinearProgress, Button } from '@mui/material';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { theme } from '../theme/index.js';

/**
 * SignInPrompt component - Full-screen sign-in prompt
 * @param {object} props
 * @param {function} props.onSignIn - Sign-in handler
 * @param {boolean} props.disabled - Whether sign-in button is disabled
 */
export const SignInPrompt = ({ onSignIn, disabled }) => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 3,
          bgcolor: 'background.default',
          p: 3,
        }}
      >
        <Paper sx={{ p: 4, maxWidth: 420, textAlign: 'center' }} elevation={6}>
          <Typography variant="h5" gutterBottom>
            Sign in to continue
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            This workspace requires Microsoft Entra ID authentication before showing the agents.
          </Typography>
          <LinearProgress sx={{ mb: 2 }} />
          <Button variant="contained" onClick={onSignIn} disabled={disabled}>
            Sign in with Microsoft
          </Button>
        </Paper>
      </Box>
    </ThemeProvider>
  );
};
