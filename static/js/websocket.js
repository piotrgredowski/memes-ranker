/**
 * WebSocket Service for real-time updates in Memes Ranker
 */

class WebSocketService {
    constructor(endpoint, reconnectInterval = 5000) {
        this.endpoint = endpoint;
        this.reconnectInterval = reconnectInterval;
        this.maxReconnectAttempts = 5;
        this.reconnectAttempts = 0;
        this.websocket = null;
        this.eventHandlers = new Map();
        this.connectionStatus = 'disconnected';
        this.isManualClose = false;

        // Bind methods to preserve 'this' context
        this.connect = this.connect.bind(this);
        this.onOpen = this.onOpen.bind(this);
        this.onMessage = this.onMessage.bind(this);
        this.onClose = this.onClose.bind(this);
        this.onError = this.onError.bind(this);

        // Start connection
        this.connect();
    }

    connect() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            return; // Already connected
        }

        try {
            this.setConnectionStatus('connecting');

            // Create WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const wsUrl = `${protocol}//${host}${this.endpoint}`;

            console.log(`[WebSocket] Connecting to ${wsUrl}`);
            this.websocket = new WebSocket(wsUrl);

            // Set up event listeners
            this.websocket.addEventListener('open', this.onOpen);
            this.websocket.addEventListener('message', this.onMessage);
            this.websocket.addEventListener('close', this.onClose);
            this.websocket.addEventListener('error', this.onError);

        } catch (error) {
            console.error('[WebSocket] Connection error:', error);
            this.scheduleReconnect();
        }
    }

    onOpen(event) {
        console.log('[WebSocket] Connected successfully');
        this.setConnectionStatus('connected');
        this.reconnectAttempts = 0;

        // Trigger connected event
        this.triggerEvent('connected', { timestamp: new Date().toISOString() });
    }

    onMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('[WebSocket] Message received:', message);

            // Handle different message types
            if (message.type) {
                this.triggerEvent(message.type, message.data || message);
            }

            // Handle ping/pong for connection health
            if (message.type === 'ping') {
                this.send({ type: 'pong', timestamp: new Date().toISOString() });
            }

        } catch (error) {
            console.error('[WebSocket] Error parsing message:', error);
        }
    }

    onClose(event) {
        console.log('[WebSocket] Connection closed:', event.code, event.reason);
        this.setConnectionStatus('disconnected');

        // Trigger disconnected event
        this.triggerEvent('disconnected', {
            code: event.code,
            reason: event.reason,
            timestamp: new Date().toISOString()
        });

        // Attempt to reconnect if not manually closed
        if (!this.isManualClose && event.code !== 1000) {
            this.scheduleReconnect();
        }
    }

    onError(event) {
        console.error('[WebSocket] Error:', event);
        this.setConnectionStatus('error');

        // Trigger error event
        this.triggerEvent('error', {
            error: event,
            timestamp: new Date().toISOString()
        });
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[WebSocket] Max reconnection attempts reached');
            this.setConnectionStatus('failed');
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000); // Exponential backoff, max 30s

        console.log(`[WebSocket] Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
        this.setConnectionStatus('reconnecting');

        setTimeout(() => {
            if (!this.isManualClose) {
                this.connect();
            }
        }, delay);
    }

    send(data) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            try {
                const message = typeof data === 'string' ? data : JSON.stringify(data);
                this.websocket.send(message);
                return true;
            } catch (error) {
                console.error('[WebSocket] Error sending message:', error);
                return false;
            }
        } else {
            console.warn('[WebSocket] Cannot send message - not connected');
            return false;
        }
    }

    addEventListener(eventType, handler) {
        if (!this.eventHandlers.has(eventType)) {
            this.eventHandlers.set(eventType, []);
        }
        this.eventHandlers.get(eventType).push(handler);
    }

    removeEventListener(eventType, handler) {
        if (this.eventHandlers.has(eventType)) {
            const handlers = this.eventHandlers.get(eventType);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    triggerEvent(eventType, data) {
        if (this.eventHandlers.has(eventType)) {
            const handlers = this.eventHandlers.get(eventType);
            handlers.forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`[WebSocket] Error in event handler for ${eventType}:`, error);
                }
            });
        }
    }

    setConnectionStatus(status) {
        const oldStatus = this.connectionStatus;
        this.connectionStatus = status;

        if (oldStatus !== status) {
            console.log(`[WebSocket] Status changed: ${oldStatus} -> ${status}`);
            this.triggerEvent('status_changed', {
                old_status: oldStatus,
                new_status: status,
                timestamp: new Date().toISOString()
            });
        }
    }

    getConnectionStatus() {
        return this.connectionStatus;
    }

    isConnected() {
        return this.connectionStatus === 'connected';
    }

    disconnect() {
        this.isManualClose = true;
        if (this.websocket) {
            this.websocket.close(1000, 'Manual disconnect');
        }
        this.setConnectionStatus('disconnected');
    }

    reconnect() {
        this.isManualClose = false;
        this.reconnectAttempts = 0;
        this.connect();
    }
}

/**
 * WebSocket Service Manager - Singleton pattern for managing connections
 */
class WebSocketManager {
    constructor() {
        this.services = new Map();
    }

    createService(name, endpoint, options = {}) {
        if (this.services.has(name)) {
            console.warn(`[WebSocketManager] Service ${name} already exists`);
            return this.services.get(name);
        }

        const service = new WebSocketService(endpoint, options.reconnectInterval);
        this.services.set(name, service);

        console.log(`[WebSocketManager] Created service: ${name}`);
        return service;
    }

    getService(name) {
        return this.services.get(name);
    }

    destroyService(name) {
        const service = this.services.get(name);
        if (service) {
            service.disconnect();
            this.services.delete(name);
            console.log(`[WebSocketManager] Destroyed service: ${name}`);
        }
    }

    destroyAllServices() {
        this.services.forEach((service, name) => {
            service.disconnect();
            console.log(`[WebSocketManager] Destroyed service: ${name}`);
        });
        this.services.clear();
    }
}

// Global WebSocket manager instance
window.wsManager = new WebSocketManager();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { WebSocketService, WebSocketManager };
}
