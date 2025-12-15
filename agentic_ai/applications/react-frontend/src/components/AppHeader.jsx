import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Add as AddIcon,
} from '@mui/icons-material';
import { AgentSelector } from './AgentSelector.jsx';

/**
 * AppHeader component - Top application bar with controls
 * @param {object} props
 * @param {boolean} props.isAuthEnabled - Whether authentication is enabled
 * @param {boolean} props.isSignedIn - Whether user is signed in
 * @param {object} props.account - User account object
 * @param {function} props.onSignIn - Sign-in handler
 * @param {function} props.onSignOut - Sign-out handler
 * @param {boolean} props.authConfigLoaded - Whether auth config has loaded
 * @param {Array} props.availableAgents - Available agents
 * @param {string} props.currentAgent - Current agent module path
 * @param {function} props.onAgentChange - Agent change handler
 * @param {boolean} props.isProcessing - Whether processing is active
 * @param {boolean} props.canInteract - Whether user can interact
 * @param {function} props.onNewSession - New session handler
 * @param {boolean} props.showInternalProcess - Whether internal process is shown
 * @param {function} props.onToggleInternalProcess - Toggle internal process handler
 */
export const AppHeader = ({
  isAuthEnabled,
  isSignedIn,
  account,
  onSignIn,
  onSignOut,
  authConfigLoaded,
  availableAgents,
  currentAgent,
  onAgentChange,
  isProcessing,
  canInteract,
  onNewSession,
  showInternalProcess,
  onToggleInternalProcess,
}) => {
  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          🤖 Magentic AI Assistant
        </Typography>

        {isAuthEnabled && (
          isSignedIn ? (
            <Button color="inherit" onClick={onSignOut} sx={{ mr: 2 }}>
              Sign out {account?.username ? `(${account.username})` : ''}
            </Button>
          ) : (
            <Button color="inherit" onClick={onSignIn} disabled={!authConfigLoaded} sx={{ mr: 2 }}>
              Sign in
            </Button>
          )
        )}
        
        <AgentSelector
          agents={availableAgents}
          currentAgent={currentAgent}
          onChange={onAgentChange}
          disabled={isProcessing || !canInteract}
        />
        
        <Button
          color="inherit"
          onClick={onNewSession}
          startIcon={<AddIcon />}
          sx={{ mr: 2 }}
          disabled={!canInteract}
        >
          New Session
        </Button>
        
        <IconButton
          color="inherit"
          onClick={onToggleInternalProcess}
        >
          {showInternalProcess ? <VisibilityOffIcon /> : <VisibilityIcon />}
        </IconButton>
      </Toolbar>
    </AppBar>
  );
};
