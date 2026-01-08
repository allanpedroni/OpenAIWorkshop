import { useState, useEffect, useRef, useCallback } from 'react';
import { WebSocketManager } from '../services/websocket.js';

/**
 * Custom hook for managing WebSocket connection and message handling
 * @param {string} sessionId - Current session ID
 * @param {boolean} isAuthEnabled - Whether authentication is enabled
 * @param {string} accessToken - Access token for authenticated requests
 * @param {boolean} authConfigLoaded - Whether auth config has loaded
 * @param {function} onChatEvent - Callback for chat-related events
 * @returns {object} WebSocket state and utilities
 */
export const useWebSocket = (sessionId, isAuthEnabled, accessToken, authConfigLoaded, onChatEvent) => {
  const [orchestratorEvents, setOrchestratorEvents] = useState([]);
  const [agentEvents, setAgentEvents] = useState({});
  const [currentAgents, setCurrentAgents] = useState(new Set());
  const [currentTurn, setCurrentTurn] = useState(0);
  const [lastFinalAnswer, setLastFinalAnswer] = useState(null);

  const wsManagerRef = useRef(null);
  const onChatEventRef = useRef(onChatEvent);

  // Keep callback ref updated
  useEffect(() => {
    onChatEventRef.current = onChatEvent;
  }, [onChatEvent]);

  /**
   * Handle incoming WebSocket messages
   */
  const handleWebSocketMessage = useCallback((event) => {
    const { type } = event;

    switch (type) {
      case 'orchestrator':
        setOrchestratorEvents((prev) => {
          const lastEvent = prev[prev.length - 1];
          // Skip duplicates
          if (lastEvent && lastEvent.kind === event.kind && lastEvent.content === event.content) {
            return prev;
          }
          return [...prev, event];
        });
        break;

      case 'agent_start':
        setCurrentAgents((prev) => new Set([...prev, event.agent_id]));
        setAgentEvents((prev) => {
          if (prev[event.agent_id]) {
            return prev;
          }
          return {
            ...prev,
            [event.agent_id]: {
              name: event.agent_name || event.agent_id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
              tokens: [],
              complete: false,
              showMessageInInternalProcess: event.show_message_in_internal_process !== false,
            },
          };
        });
        break;

      case 'agent_token':
        setAgentEvents((prev) => ({
          ...prev,
          [event.agent_id]: {
            ...prev[event.agent_id],
            tokens: [...(prev[event.agent_id]?.tokens || []), event.content],
          },
        }));
        break;

      case 'agent_message':
        setCurrentAgents((prev) => {
          const newSet = new Set(prev);
          newSet.delete(event.agent_id);
          return newSet;
        });
        setAgentEvents((prev) => {
          const existing = prev[event.agent_id];
          if (existing?.complete && existing.finalMessage === event.content) {
            return prev;
          }
          return {
            ...prev,
            [event.agent_id]: {
              ...existing,
              finalMessage: event.content,
              complete: true,
            },
          };
        });
        break;

      case 'tool_called':
        setAgentEvents((prev) => {
          const agentId = event.agent_id || 'single_agent';
          const existing = prev[agentId] || { name: agentId, tokens: [], toolCallsByTurn: {} };
          
          const turnNumber = event.turn !== undefined ? event.turn : currentTurn;
          const toolCallsByTurn = existing.toolCallsByTurn || {};
          const turnTools = toolCallsByTurn[turnNumber] || [];
          
          if (!turnTools.includes(event.tool_name)) {
            turnTools.push(event.tool_name);
            toolCallsByTurn[turnNumber] = turnTools;
          }
          
          return {
            ...prev,
            [agentId]: {
              ...existing,
              toolCallsByTurn,
            },
          };
        });
        break;

      case 'final_result':
      case 'message':
      case 'done':
      case 'error':
        // Forward to chat event handler
        if (onChatEventRef.current) {
          onChatEventRef.current(event);
        }
        break;

      default:
        break;
    }
  }, [currentTurn]);

  /**
   * Initialize WebSocket connection
   */
  useEffect(() => {
    if (isAuthEnabled && !accessToken) {
      if (wsManagerRef.current) {
        wsManagerRef.current.close();
        wsManagerRef.current = null;
      }
      return;
    }

    if (!authConfigLoaded) {
      return;
    }

    wsManagerRef.current = new WebSocketManager();
    wsManagerRef.current.connect(
      sessionId,
      handleWebSocketMessage,
      accessToken,
      isAuthEnabled
    );

    return () => {
      if (wsManagerRef.current) {
        wsManagerRef.current.close();
      }
    };
  }, [sessionId, isAuthEnabled, accessToken, authConfigLoaded, handleWebSocketMessage]);

  /**
   * Send a message through WebSocket
   */
  const sendMessage = (prompt) => {
    if (wsManagerRef.current && wsManagerRef.current.isConnected()) {
      wsManagerRef.current.send({
        session_id: sessionId,
        prompt,
        access_token: isAuthEnabled ? accessToken : null,
      });
      return true;
    }
    return false;
  };

  /**
   * Reset internal process state
   */
  const resetInternalProcess = () => {
    setOrchestratorEvents([]);
    setAgentEvents({});
    setCurrentAgents(new Set());
    setCurrentTurn(0);
    setLastFinalAnswer(null);
  };

  /**
   * Increment turn counter
   */
  const incrementTurn = () => {
    setCurrentTurn((prev) => prev + 1);
  };

  return {
    orchestratorEvents,
    agentEvents,
    currentAgents,
    currentTurn,
    lastFinalAnswer,
    sendMessage,
    resetInternalProcess,
    incrementTurn,
    isConnected: wsManagerRef.current?.isConnected() || false,
  };
};
