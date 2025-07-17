/**
 * Frontend Logger for Memes Ranker
 *
 * Provides client-side logging that batches and sends logs to the backend
 * for storage in frontend.log and frontend_json.log files.
 */

class FrontendLogger {
    /**
     * Initialize the frontend logger
     * @param {Object} options - Configuration options
     * @param {string} options.apiEndpoint - API endpoint for sending logs
     * @param {number} options.batchSize - Number of logs to batch before sending
     * @param {number} options.flushInterval - Interval in ms to flush logs
     * @param {number} options.maxRetries - Maximum number of retry attempts
     * @param {string} options.sessionId - Session ID for this user
     * @param {string} options.userId - User ID for this user
     * @param {string} options.logLevel - Minimum log level to capture
     */
    constructor(options = {}) {
        this.apiEndpoint = options.apiEndpoint || '/api/frontend-logs';
        this.batchSize = options.batchSize || 10;
        this.flushInterval = options.flushInterval || 5000; // 5 seconds
        this.maxRetries = options.maxRetries || 3;
        this.sessionId = options.sessionId || this.getSessionId();
        this.userId = options.userId || this.getUserId();
        this.logLevel = options.logLevel || 'info';

        // Internal state
        this.logBuffer = [];
        this.flushTimer = null;
        this.isOnline = navigator.onLine;
        this.retryQueue = [];

        // Log levels (higher number = more severe)
        this.logLevels = {
            'debug': 0,
            'info': 1,
            'warn': 2,
            'error': 3
        };

        // Start the flush timer
        this.startBatchTimer();

        // Setup error handlers
        this.setupErrorHandlers();

        // Monitor online/offline status
        this.setupNetworkMonitoring();

        // Log that the logger has been initialized
        this.info('Frontend logger initialized', {
            component: 'frontend-logger',
            action: 'init',
            config: {
                batchSize: this.batchSize,
                flushInterval: this.flushInterval,
                logLevel: this.logLevel
            }
        });
    }

    /**
     * Get session ID from cookies or storage
     */
    getSessionId() {
        // Try to get from cookie first
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'session_token') {
                return value;
            }
        }

        // Try localStorage as fallback
        return localStorage.getItem('session_id') || null;
    }

    /**
     * Get user ID from page context or storage
     */
    getUserId() {
        // Try to get from global variable set by template
        if (typeof window.userName !== 'undefined') {
            return window.userName;
        }

        // Try localStorage as fallback
        return localStorage.getItem('user_id') || null;
    }

    /**
     * Get client info for logging
     */
    getClientInfo() {
        const nav = navigator;
        const screen = window.screen;

        return {
            user_agent: nav.userAgent,
            platform: nav.platform,
            language: nav.language,
            screen_resolution: `${screen.width}x${screen.height}`,
            viewport_size: `${window.innerWidth}x${window.innerHeight}`,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            online: nav.onLine,
            cookies_enabled: nav.cookieEnabled,
            url: window.location.href,
            referrer: document.referrer || null
        };
    }

    /**
     * Check if a log level should be captured
     */
    shouldLog(level) {
        const levelNum = this.logLevels[level.toLowerCase()];
        const minLevelNum = this.logLevels[this.logLevel.toLowerCase()];
        return levelNum >= minLevelNum;
    }

    /**
     * Create a log entry
     */
    createLogEntry(level, message, metadata = {}) {
        return {
            level: level.toLowerCase(),
            message: message,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            user_agent: navigator.userAgent,
            session_id: this.sessionId,
            user_id: this.userId,
            component: metadata.component || null,
            action: metadata.action || null,
            metadata: metadata.metadata || metadata,
            stack_trace: metadata.stack_trace || null
        };
    }

    /**
     * Add a log entry to the buffer
     */
    addToBuffer(level, message, metadata = {}) {
        if (!this.shouldLog(level)) {
            return;
        }

        const logEntry = this.createLogEntry(level, message, metadata);
        this.logBuffer.push(logEntry);

        // If buffer is full, flush immediately
        if (this.logBuffer.length >= this.batchSize) {
            this.flush();
        }
    }

    /**
     * Debug level logging
     */
    debug(message, metadata = {}) {
        this.addToBuffer('debug', message, metadata);
    }

    /**
     * Info level logging
     */
    info(message, metadata = {}) {
        this.addToBuffer('info', message, metadata);
    }

    /**
     * Warning level logging
     */
    warn(message, metadata = {}) {
        this.addToBuffer('warn', message, metadata);
    }

    /**
     * Error level logging
     */
    error(message, metadata = {}) {
        this.addToBuffer('error', message, metadata);
    }

    /**
     * Start the batch timer
     */
    startBatchTimer() {
        if (this.flushTimer) {
            clearInterval(this.flushTimer);
        }

        this.flushTimer = setInterval(() => {
            if (this.logBuffer.length > 0) {
                this.flush();
            }
        }, this.flushInterval);
    }

    /**
     * Flush logs to the server
     */
    async flush() {
        if (this.logBuffer.length === 0) {
            return;
        }

        const logsToSend = [...this.logBuffer];
        this.logBuffer = [];

        const batch = {
            logs: logsToSend,
            client_info: this.getClientInfo()
        };

        try {
            await this.sendBatch(batch);
        } catch (error) {
            // Add failed logs to retry queue
            this.retryQueue.push({
                batch: batch,
                attempts: 0,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Send a batch of logs to the server
     */
    async sendBatch(batch, retryCount = 0) {
        if (!this.isOnline) {
            throw new Error('Offline');
        }

        const response = await fetch(this.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(batch)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    /**
     * Retry failed log batches
     */
    async retryFailedBatches() {
        if (!this.isOnline || this.retryQueue.length === 0) {
            return;
        }

        const now = Date.now();
        const retryDelay = 5000; // 5 seconds

        for (let i = this.retryQueue.length - 1; i >= 0; i--) {
            const queueItem = this.retryQueue[i];

            // Skip if not enough time has passed
            if (now - queueItem.timestamp < retryDelay) {
                continue;
            }

            // Remove if too many attempts
            if (queueItem.attempts >= this.maxRetries) {
                this.retryQueue.splice(i, 1);
                continue;
            }

            try {
                await this.sendBatch(queueItem.batch);
                this.retryQueue.splice(i, 1); // Remove on success
            } catch (error) {
                queueItem.attempts++;
                queueItem.timestamp = now;
            }
        }
    }

    /**
     * Setup global error handlers
     */
    setupErrorHandlers() {
        // Global JavaScript errors
        window.addEventListener('error', (event) => {
            this.error('JavaScript Error', {
                component: 'global-error-handler',
                action: 'javascript-error',
                metadata: {
                    message: event.message,
                    filename: event.filename,
                    lineno: event.lineno,
                    colno: event.colno,
                    error_type: event.error?.name || 'Error'
                },
                stack_trace: event.error?.stack || null
            });
        });

        // Unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.error('Unhandled Promise Rejection', {
                component: 'global-error-handler',
                action: 'promise-rejection',
                metadata: {
                    reason: event.reason?.toString() || 'Unknown',
                    promise: event.promise?.toString() || 'Unknown'
                },
                stack_trace: event.reason?.stack || null
            });
        });

        // Resource loading errors
        window.addEventListener('error', (event) => {
            if (event.target !== window) {
                this.error('Resource Load Error', {
                    component: 'global-error-handler',
                    action: 'resource-error',
                    metadata: {
                        element: event.target.tagName,
                        source: event.target.src || event.target.href,
                        type: event.target.type || 'unknown'
                    }
                });
            }
        }, true);
    }

    /**
     * Setup network monitoring
     */
    setupNetworkMonitoring() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.info('Network status changed', {
                component: 'network-monitor',
                action: 'online'
            });
            // Retry failed batches when back online
            this.retryFailedBatches();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.warn('Network status changed', {
                component: 'network-monitor',
                action: 'offline'
            });
        });
    }

    /**
     * Log page performance metrics
     */
    logPerformanceMetrics() {
        if (!window.performance || !window.performance.timing) {
            return;
        }

        const timing = window.performance.timing;
        const navigation = timing.navigationStart;

        const metrics = {
            dns_lookup: timing.domainLookupEnd - timing.domainLookupStart,
            tcp_connect: timing.connectEnd - timing.connectStart,
            request_time: timing.responseStart - timing.requestStart,
            response_time: timing.responseEnd - timing.responseStart,
            dom_processing: timing.domComplete - timing.domLoading,
            page_load: timing.loadEventEnd - navigation,
            dom_ready: timing.domContentLoadedEventEnd - navigation,
            first_paint: null,
            largest_contentful_paint: null
        };

        // Try to get paint timings
        if (window.performance.getEntriesByType) {
            const paintEntries = window.performance.getEntriesByType('paint');
            for (const entry of paintEntries) {
                if (entry.name === 'first-paint') {
                    metrics.first_paint = entry.startTime;
                } else if (entry.name === 'first-contentful-paint') {
                    metrics.first_contentful_paint = entry.startTime;
                }
            }

            // Try to get LCP
            const lcpEntries = window.performance.getEntriesByType('largest-contentful-paint');
            if (lcpEntries.length > 0) {
                metrics.largest_contentful_paint = lcpEntries[lcpEntries.length - 1].startTime;
            }
        }

        this.info('Performance metrics captured', {
            component: 'performance-monitor',
            action: 'page-load',
            metadata: metrics
        });
    }

    /**
     * Log user interaction
     */
    logUserInteraction(element, action, metadata = {}) {
        this.info(`User ${action}`, {
            component: 'user-interaction',
            action: action,
            metadata: {
                element: element.tagName,
                id: element.id || null,
                class: element.className || null,
                text: element.textContent?.substring(0, 100) || null,
                ...metadata
            }
        });
    }

    /**
     * Cleanup on page unload
     */
    cleanup() {
        if (this.flushTimer) {
            clearInterval(this.flushTimer);
        }

        // Final flush attempt
        if (this.logBuffer.length > 0) {
            // Use sendBeacon for reliable delivery during page unload
            const batch = {
                logs: this.logBuffer,
                client_info: this.getClientInfo()
            };

            if (navigator.sendBeacon) {
                navigator.sendBeacon(this.apiEndpoint, JSON.stringify(batch));
            }
        }
    }
}

// Initialize logger when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Get user info from page context
    const userName = document.querySelector('meta[name="user-name"]')?.content;
    const sessionToken = document.querySelector('meta[name="session-token"]')?.content;

    // Initialize global logger
    window.logger = new FrontendLogger({
        sessionId: sessionToken,
        userId: userName,
        logLevel: 'info'
    });

    // Setup page unload handler
    window.addEventListener('beforeunload', () => {
        window.logger.cleanup();
    });

    // Log performance metrics when page is loaded
    window.addEventListener('load', () => {
        setTimeout(() => {
            window.logger.logPerformanceMetrics();
        }, 100);
    });
});

// Make logger available globally
window.FrontendLogger = FrontendLogger;
