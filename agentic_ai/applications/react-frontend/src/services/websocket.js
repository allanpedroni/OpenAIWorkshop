import { WS_URL, WS_RECONNECT_DELAY } from '../constants/index.js';

/**
 * WebSocket manager class to handle connection lifecycle
 */
export class WebSocketManager {
  constructor() {
    this.ws = null;
    this.sessionId = null;
    this.accessToken = null;
    this.isAuthEnabled = false;
    this.onMessageCallback = null;
    this.reconnectTimeout = null;
  }

  /**
   * Connect to the WebSocket server
   * @param {string} sessionId - Session identifier
   * @param {function} onMessage - Callback for incoming messages
   * @param {string} accessToken - Optional access token for auth
   * @param {boolean} isAuthEnabled - Whether auth is enabled
   */
  connect(sessionId, onMessage, accessToken = null, isAuthEnabled = false) {
    this.sessionId = sessionId;
    this.onMessageCallback = onMessage;
    this.accessToken = accessToken;
    this.isAuthEnabled = isAuthEnabled;

    this.ws = new WebSocket(WS_URL);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      // Register session
      this.send({
        session_id: this.sessionId,
        access_token: this.isAuthEnabled ? this.accessToken : null,
      });
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (this.onMessageCallback) {
        this.onMessageCallback(data);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      // Reconnect after delay
      this.reconnectTimeout = setTimeout(() => {
        this.connect(this.sessionId, this.onMessageCallback, this.accessToken, this.isAuthEnabled);
      }, WS_RECONNECT_DELAY);
    };
  }

  /**
   * Send a message through the WebSocket
   * @param {object} message - Message to send
   */
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  /**
   * Close the WebSocket connection
   */
  close() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Check if WebSocket is connected
   * @returns {boolean}
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}
