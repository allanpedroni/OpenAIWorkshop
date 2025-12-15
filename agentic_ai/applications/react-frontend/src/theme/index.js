import { createTheme } from '@mui/material';

/**
 * Application theme configuration
 * Defines the color palette, typography, and other theme settings
 */
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
  },
});

/**
 * Event type colors for orchestrator events
 */
export const eventColors = {
  instruction: { bgColor: '#f3e5f5', color: 'secondary' },
  task_ledger: { bgColor: '#e3f2fd', color: 'info' },
  user_task: { bgColor: '#f5f5f5', color: 'default' },
  notice: { bgColor: '#fff3e0', color: 'warning' },
  plan: { bgColor: '#e3f2fd', color: 'primary' },
  progress: { bgColor: '#e1f5fe', color: 'info' },
  result: { bgColor: '#e8f5e9', color: 'success' },
  default: { bgColor: '#f5f5f5', color: 'default' },
};

/**
 * Message background colors
 */
export const messageColors = {
  user: '#e3f2fd',
  assistant: '#ffffff',
  error: '#ffebee',
};
