import { useState } from 'react';

/**
 * Custom hook for managing chat messages and processing state
 * @returns {object} Chat state and methods
 */
export const useChat = () => {
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastFinalAnswer, setLastFinalAnswer] = useState(null);

  /**
   * Add a user message
   * @param {string} content - Message content
   */
  const addUserMessage = (content) => {
    setMessages((prev) => [
      ...prev,
      {
        role: 'user',
        content,
        timestamp: new Date(),
      },
    ]);
  };

  /**
   * Add an assistant message with deduplication
   * @param {string} content - Message content
   * @returns {boolean} Whether the message was added
   */
  const addAssistantMessage = (content) => {
    let wasAdded = false;
    setMessages((prev) => {
      const lastMsg = prev[prev.length - 1];
      if (lastMsg && lastMsg.role === 'assistant' && lastMsg.content === content) {
        console.log('[DEDUP] Skipping duplicate assistant message');
        return prev;
      }
      wasAdded = true;
      return [
        ...prev,
        {
          role: 'assistant',
          content,
          timestamp: new Date(),
        },
      ];
    });
    if (wasAdded) {
      setLastFinalAnswer(content);
    }
    return wasAdded;
  };

  /**
   * Add an error message
   * @param {string} content - Error content
   */
  const addErrorMessage = (content) => {
    setMessages((prev) => [
      ...prev,
      {
        role: 'error',
        content,
        timestamp: new Date(),
      },
    ]);
  };

  /**
   * Handle WebSocket events related to chat
   * @param {object} event - WebSocket event
   */
  const handleChatEvent = (event) => {
    const { type } = event;

    switch (type) {
      case 'final_result':
      case 'message':
        if (event.content) {
          addAssistantMessage(event.content);
        }
        setIsProcessing(false);
        break;

      case 'done':
        setIsProcessing(false);
        break;

      case 'error':
        addErrorMessage(`Error: ${event.message}`);
        setIsProcessing(false);
        break;

      default:
        break;
    }
  };

  /**
   * Clear all messages
   */
  const clearMessages = () => {
    setMessages([]);
    setLastFinalAnswer(null);
  };

  /**
   * Start processing
   */
  const startProcessing = () => {
    setIsProcessing(true);
    setLastFinalAnswer(null);
  };

  /**
   * Stop processing
   */
  const stopProcessing = () => {
    setIsProcessing(false);
  };

  return {
    messages,
    isProcessing,
    lastFinalAnswer,
    addUserMessage,
    addAssistantMessage,
    addErrorMessage,
    handleChatEvent,
    clearMessages,
    startProcessing,
    stopProcessing,
  };
};
