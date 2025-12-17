import { useState, useCallback, useEffect } from 'react';
import {
  Box,
  ThemeProvider,
  CssBaseline,
  AppBar,
  Toolbar,
  Typography,
  Paper,
  Grid,
} from '@mui/material';
import SecurityIcon from '@mui/icons-material/Security';
import WorkflowVisualizer from './components/WorkflowVisualizer';
import ControlPanel from './components/ControlPanel';
import AnalystDecisionPanel from './components/AnalystDecisionPanel';
import EventLog from './components/EventLog';
import { useWebSocket } from './hooks/useWebSocket';
import { fetchAlerts, startWorkflow, submitDecision } from './utils/api';
import { isDuplicateEvent } from './utils/helpers';
import { EVENT_TYPES } from './constants/workflow';
import { API_CONFIG, APP_CONFIG } from './constants/config';
import theme from './theme';

/**
 * Main application component for the Fraud Detection Workflow Visualizer
 * Manages the state and orchestration of workflow visualization, controls, and event logging
 */
function App() {
  // State management
  const [alerts, setAlerts] = useState([]);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [workflowRunning, setWorkflowRunning] = useState(false);
  const [events, setEvents] = useState([]);
  const [pendingDecision, setPendingDecision] = useState(null);
  const [executorStates, setExecutorStates] = useState({});

  // WebSocket connection for real-time updates
  const { lastMessage, sendMessage } = useWebSocket(API_CONFIG.WS_URL);

  /**
   * Load sample alerts on component mount
   */
  useEffect(() => {
    const loadAlerts = async () => {
      try {
        const alertsData = await fetchAlerts();
        setAlerts(alertsData);
      } catch (error) {
        console.error('Failed to load alerts:', error);
      }
    };

    loadAlerts();
  }, []);

  /**
   * Handle incoming WebSocket messages
   * Process different event types and update application state accordingly
   */
  useEffect(() => {
    if (!lastMessage) return;

    try {
      const event = lastMessage;

      // Add to event log - prevent duplicates
      setEvents((prev) => {
        return isDuplicateEvent(event, prev) ? prev : [...prev, event];
      });

      // Handle workflow initialization
      if (event.type === EVENT_TYPES.WORKFLOW_INITIALIZING) {
        // Keep workflow running flag true, just show initialization message
      }

      // Handle workflow started
      if (event.type === EVENT_TYPES.WORKFLOW_STARTED) {
        // Workflow is now running
      }

      // Update executor states based on event type
      if (event.event_type === EVENT_TYPES.EXECUTOR_INVOKED) {
        setExecutorStates((prev) => ({
          ...prev,
          [event.executor_id]: 'running',
        }));
      } else if (event.event_type === EVENT_TYPES.EXECUTOR_COMPLETED) {
        setExecutorStates((prev) => ({
          ...prev,
          [event.executor_id]: 'completed',
        }));
      }

      // Handle decision required
      if (event.type === EVENT_TYPES.DECISION_REQUIRED) {
        setPendingDecision(event);
        setWorkflowRunning(false);
      }

      // Handle workflow completion
      if (event.type === EVENT_TYPES.WORKFLOW_COMPLETED || event.type === EVENT_TYPES.WORKFLOW_ERROR) {
        setWorkflowRunning(false);
        // Keep all executor states as-is (they should already be 'completed')
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
    }
  }, [lastMessage]);

  /**
   * Start a workflow for the selected alert
   * @param {Object} alert - The alert object to process
   */
  const handleStartWorkflow = useCallback(async (alert) => {
    console.log('Starting workflow for alert:', alert);
    setSelectedAlert(alert);
    setWorkflowRunning(true);
    setEvents([]);
    setExecutorStates({});
    setPendingDecision(null);

    try {
      const data = await startWorkflow(alert);
      console.log('Workflow started:', data);
    } catch (error) {
      console.error('Error starting workflow:', error);
      setWorkflowRunning(false);
    }
  }, []);

  /**
   * Submit analyst decision and resume workflow
   * @param {Object} decision - The decision object containing analyst's input
   */
  const handleSubmitDecision = useCallback(async (decision) => {
    console.log('Submitting decision:', decision);

    try {
      const data = await submitDecision(decision);
      console.log('Decision submitted:', data);

      setPendingDecision(null);
      setWorkflowRunning(true);
    } catch (error) {
      console.error('Error submitting decision:', error);
    }
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100%' }}>
        {/* App Bar */}
        <AppBar position="static" elevation={2}>
          <Toolbar>
            <SecurityIcon sx={{ mr: 2 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              {APP_CONFIG.TITLE}
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Real-time Multi-Agent Workflow Monitoring
            </Typography>
          </Toolbar>
        </AppBar>

        {/* Main Content */}
        <Box sx={{ flex: 1, p: 2, overflow: 'hidden', width: '100%' }}>
          <Grid container spacing={2} sx={{ height: '100%' }}>
            {/* Left Column - Controls and Decision Panel */}
            <Grid size={{ xs: 12, md: 2 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%' }}>
                <ControlPanel
                  alerts={alerts}
                  onStartWorkflow={handleStartWorkflow}
                  workflowRunning={workflowRunning}
                  selectedAlert={selectedAlert}
                />

                {pendingDecision && (
                  <AnalystDecisionPanel
                    decision={pendingDecision}
                    onSubmit={handleSubmitDecision}
                  />
                )}
              </Box>
            </Grid>

            {/* Center Column - Workflow Visualization */}
            <Grid size={{ xs: 12, md: 7.5 }}>
              <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                  <Typography variant="h6">Workflow Graph</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {selectedAlert
                      ? `Alert: ${selectedAlert.alert_id} - ${selectedAlert.description}`
                      : 'Select an alert to start'}
                  </Typography>
                </Box>
                <Box sx={{ flex: 1, position: 'relative' }}>
                  <WorkflowVisualizer executorStates={executorStates} />
                </Box>
              </Paper>
            </Grid>

            {/* Right Column - Event Log */}
            <Grid size={{ xs: 12, md: 2.5 }}>
              <EventLog events={events} />
            </Grid>
          </Grid>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
