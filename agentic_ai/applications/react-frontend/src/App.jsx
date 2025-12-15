import React, { useState, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import {
  Box,
  Container,
  Paper,
  LinearProgress,
  Typography,
  ThemeProvider,
  CssBaseline,
} from '@mui/material';
import { theme } from './theme/index.js';
import { NotificationProvider, useNotification } from './contexts/NotificationContext.jsx';
import { useAuth, useAgents, useChat, useWebSocket } from './hooks/index.js';
import {
  AppHeader,
  ChatMessage,
  ChatInput,
  InternalProcessDrawer,
  GlobalNotification,
  SignInPrompt,
  ErrorBoundary,
} from './components/index.js';
import { resetSession } from './services/api.js';
import { scrollToRef } from './utils/helpers.jsx';

/**
 * Main App Component
 * Orchestrates the Magentic AI Assistant application
 */
function AppContent() {
  // Session management
  const [sessionId, setSessionId] = useState(() => uuidv4());
  const [input, setInput] = useState('');
  const [showInternalProcess, setShowInternalProcess] = useState(true);

  // Notification context
  const { showError, showSuccess, showWarning } = useNotification();

  // Refs for auto-scrolling
  const messagesEndRef = useRef(null);

  // Authentication hook
  const {
    authConfig,
    authConfigLoaded,
    isAuthEnabled,
    isSignedIn,
    account,
    accessToken,
    signIn,
    signOut,
    error: authError,
  } = useAuth();

  // Show auth errors using notification
  useEffect(() => {
    if (authError) {
      showError(`Authentication configuration error: ${authError}. Running in non-authenticated mode.`);
    }
  }, [authError, showError]);

  // Agents hook
  const {
    availableAgents,
    currentAgent,
    loading: agentsLoading,
    error: agentsError,
    changeAgent,
  } = useAgents(authConfigLoaded, isAuthEnabled, accessToken);

  // Show agents errors using notification
  useEffect(() => {
    if (agentsError) {
      showError(`Failed to load agents: ${agentsError}`);
    }
  }, [agentsError, showError]);

  // Chat hook
  const chat = useChat();

  // WebSocket hook with chat event callback
  const ws = useWebSocket(
    sessionId, 
    isAuthEnabled, 
    accessToken, 
    authConfigLoaded,
    chat.handleChatEvent // Pass chat event handler to WebSocket
  );

  // Auto-scroll messages
  useEffect(() => {
    scrollToRef(messagesEndRef);
  }, [chat.messages]);

  // Derived state
  const canInteract = !isAuthEnabled || (isSignedIn && authConfigLoaded);
  const shouldBlockUi = isAuthEnabled && authConfigLoaded && !isSignedIn;
  const inputPlaceholder = canInteract ? 'Type your message...' : 'Sign in to chat…';

  /**
   * Handle sign-in
   */
  const handleSignIn = async () => {
    try {
      await signIn();
    } catch (error) {
      showError(error.message || 'Authentication error');
    }
  };

  /**
   * Handle sign-out
   */
  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (error) {
      showError(error.message || 'Sign out error');
    }
  };

  /**
   * Handle agent change
   */
  const handleAgentChange = async (event) => {
    const newAgentModule = event.target.value;
    
    if (isAuthEnabled && !accessToken) {
      showWarning('Sign in to change agents');
      return;
    }
    
    try {
      const success = await changeAgent(newAgentModule);
      
      if (success) {
        showSuccess(
          `Agent changed successfully to ${newAgentModule.split('.').pop().replace(/_/g, ' ')}`
        );
        
        // Start a new session when agent changes
        handleNewSession();
      }
    } catch (error) {
      showError(error.message || 'Failed to change agent');
    }
  };

  /**
   * Handle sending a message
   */
  const handleSend = () => {
    if (!input.trim() || chat.isProcessing) return;
    
    if (isAuthEnabled && !accessToken) {
      showWarning('Sign in to chat');
      return;
    }

    // Increment turn for this new request
    ws.incrementTurn();

    // Add user message
    chat.addUserMessage(input);

    // Send to backend via WebSocket
    const sent = ws.sendMessage(input);
    
    if (sent) {
      setInput('');
      chat.startProcessing();
    } else {
      showError('Connection lost. Please wait...');
    }
  };

  /**
   * Handle new session
   */
  const handleNewSession = async () => {
    if (isAuthEnabled && !accessToken) {
      showWarning('Sign in to start a session');
      return;
    }

    // Generate new session ID
    const newSessionId = uuidv4();
    
    // Clear all state
    chat.clearMessages();
    setInput('');
    chat.stopProcessing();
    ws.resetInternalProcess();

    // Call backend to reset old session (optional cleanup)
    try {
      await resetSession(sessionId, accessToken);
    } catch (error) {
      console.error('Error resetting session:', error);
      showError('Failed to reset previous session');
    }

    // Update session ID (will trigger WebSocket reconnect via useEffect)
    setSessionId(newSessionId);
  };

  /**
   * Handle key press in input
   */
  const handleKeyPress = (e) => {
    if (!canInteract) return;
    
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Show sign-in prompt if auth is required and user isn't signed in
  if (shouldBlockUi) {
    return (
      <SignInPrompt
        onSignIn={handleSignIn}
        disabled={!authConfigLoaded}
      />
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh' }}>
        {/* Internal Process Drawer */}
        <InternalProcessDrawer
          open={showInternalProcess}
          orchestratorEvents={ws.orchestratorEvents}
          agentEvents={ws.agentEvents}
          currentAgents={ws.currentAgents}
        />

        {/* Main Chat Area */}
        <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          {/* App Bar */}
          <AppHeader
            isAuthEnabled={isAuthEnabled}
            isSignedIn={isSignedIn}
            account={account}
            onSignIn={handleSignIn}
            onSignOut={handleSignOut}
            authConfigLoaded={authConfigLoaded}
            availableAgents={availableAgents}
            currentAgent={currentAgent}
            onAgentChange={handleAgentChange}
            isProcessing={chat.isProcessing}
            canInteract={canInteract}
            onNewSession={handleNewSession}
            showInternalProcess={showInternalProcess}
            onToggleInternalProcess={() => setShowInternalProcess(!showInternalProcess)}
          />

          {chat.isProcessing && <LinearProgress />}

          {/* Messages */}
          <Box
            sx={{
              flexGrow: 1,
              overflow: 'auto',
              p: 3,
              bgcolor: 'background.default',
            }}
          >
            <Container maxWidth="md">
              {chat.messages.length === 0 && (
                <Paper sx={{ p: 4, textAlign: 'center', bgcolor: 'background.paper' }}>
                  <Typography variant="h5" gutterBottom>
                    Welcome! 👋
                  </Typography>
                  <Typography color="text.secondary">
                    I'm a multi-agent AI assistant. Ask me about customer accounts, billing, promotions, or security.
                  </Typography>
                </Paper>
              )}

              {chat.messages.map((msg, idx) => (
                <ChatMessage key={idx} message={msg} />
              ))}

              <div ref={messagesEndRef} />
            </Container>
          </Box>

          {/* Input Area */}
          <Paper
            sx={{
              p: 2,
              borderTop: 1,
              borderColor: 'divider',
            }}
          >
            <Container maxWidth="md">
              <ChatInput
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onSend={handleSend}
                onKeyPress={handleKeyPress}
                disabled={chat.isProcessing || !canInteract}
                placeholder={inputPlaceholder}
              />
            </Container>
          </Paper>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

/**
 * App wrapper with providers
 */
function App() {
  return (
    <ErrorBoundary>
      <NotificationProvider>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <AppContent />
          <GlobalNotification />
        </ThemeProvider>
      </NotificationProvider>
    </ErrorBoundary>
  );
}

export default App;
