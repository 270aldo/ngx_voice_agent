/**
 * WebSocket Service for real-time updates
 * 
 * Handles WebSocket connection, authentication, and message handling
 * for the NGX Command Center dashboard.
 */

import { isAuthenticated } from './auth';
import { getCSRFToken } from './api';

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
  [key: string]: any;
}

export interface MetricUpdate {
  type: 'metric_update';
  metric_type: 'conversion' | 'performance' | 'activity';
  data: Record<string, any>;
  timestamp: string;
}

export interface ConversationUpdate {
  type: 'conversation_update';
  conversation_id: string;
  event_type: 'started' | 'message' | 'ended' | 'transferred';
  data: Record<string, any>;
  timestamp: string;
}

type EventHandler = (...args: any[]) => void;
type EventMap = Record<string, EventHandler[]>;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private pingInterval: NodeJS.Timeout | null = null;
  private isConnected = false;
  private url: string;
  private events: EventMap = {};

  constructor() {
    // Get WebSocket URL from environment or use default
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = process.env.REACT_APP_WS_URL?.replace(/^https?:\/\//, '') || window.location.host;
    this.url = `${wsProtocol}//${wsHost}/api/v1/ws`;
  }

  /**
   * Event emitter methods
   */
  on(event: string, handler: EventHandler): void {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(handler);
  }

  off(event: string, handler: EventHandler): void {
    if (!this.events[event]) return;
    this.events[event] = this.events[event].filter(h => h !== handler);
  }

  emit(event: string, ...args: any[]): void {
    if (!this.events[event]) return;
    this.events[event].forEach(handler => handler(...args));
  }

  /**
   * Connect to WebSocket server
   */
  async connect(): Promise<void> {
    if (!isAuthenticated()) {
      console.error('User not authenticated for WebSocket connection');
      this.emit('error', new Error('Authentication required'));
      return;
    }

    try {
      // Close existing connection if any
      if (this.ws) {
        this.ws.close();
      }

      // Get CSRF token for WebSocket authentication
      const csrfToken = await getCSRFToken();
      const wsUrl = csrfToken ? `${this.url}?token=${csrfToken}` : this.url;

      // Create new WebSocket connection
      this.ws = new WebSocket(wsUrl);

      // Set up event handlers
      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onclose = this.handleClose.bind(this);

    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.emit('error', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isConnected = false;
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent auto-reconnect
    
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Send a message through WebSocket
   */
  send(message: WebSocketMessage): void {
    if (!this.isConnected || !this.ws) {
      console.error('WebSocket is not connected');
      return;
    }

    try {
      this.ws.send(JSON.stringify(message));
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      this.emit('error', error);
    }
  }

  /**
   * Subscribe to a topic
   */
  subscribe(topic: string): void {
    this.send({
      type: 'subscribe',
      topic
    });
  }

  /**
   * Unsubscribe from a topic
   */
  unsubscribe(topic: string): void {
    this.send({
      type: 'unsubscribe',
      topic
    });
  }

  private handleOpen(): void {
    console.log('WebSocket connected');
    this.isConnected = true;
    this.reconnectAttempts = 0;
    this.reconnectDelay = 1000;
    
    // Start ping interval
    this.startPingInterval();
    
    // Subscribe to default topics
    this.subscribe('dashboard_metrics');
    this.subscribe('conversation_updates');
    this.subscribe('agent_status');
    
    this.emit('connected');
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      // Handle different message types
      switch (message.type) {
        case 'pong':
          // Heartbeat response
          break;
          
        case 'connection':
          this.emit('connection', message);
          break;
          
        case 'metric_update':
          this.emit('metric_update', message as MetricUpdate);
          break;
          
        case 'conversation_update':
          this.emit('conversation_update', message as ConversationUpdate);
          break;
          
        case 'agent_status':
          this.emit('agent_status', message);
          break;
          
        case 'lead_qualified':
          this.emit('lead_qualified', message);
          break;
          
        case 'pattern_detected':
          this.emit('pattern_detected', message);
          break;
          
        default:
          // Emit generic message event
          this.emit('message', message);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  private handleError(event: Event): void {
    console.error('WebSocket error:', event);
    this.emit('error', new Error('WebSocket error'));
  }

  private handleClose(event: CloseEvent): void {
    console.log('WebSocket disconnected:', event.code, event.reason);
    this.isConnected = false;
    
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }

    this.emit('disconnected', event);
    
    // Attempt to reconnect if not manually disconnected
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    // Don't reconnect if user is no longer authenticated
    if (!isAuthenticated()) {
      console.log('User not authenticated, skipping reconnect');
      return;
    }
    
    this.reconnectAttempts++;
    
    console.log(
      `Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${this.reconnectDelay}ms`
    );
    
    setTimeout(() => {
      this.connect();
    }, this.reconnectDelay);
    
    // Exponential backoff
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
  }

  private startPingInterval(): void {
    // Send ping every 30 seconds
    this.pingInterval = setInterval(() => {
      if (this.isConnected) {
        this.send({ type: 'ping' });
      }
    }, 30000);
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): boolean {
    return this.isConnected;
  }
}

// Create singleton instance
const webSocketService = new WebSocketService();

// Export service and types
export default webSocketService;
export { WebSocketService };