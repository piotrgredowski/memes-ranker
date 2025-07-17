/**
 * User View Real-time Updates
 * Handles WebSocket connections and UI updates for the user view
 */

class UserRealtimeManager {
    constructor() {
        this.wsService = null;
        this.isInitialized = false;
        this.connectionStatusElement = null;
        this.isRatingInProgress = false;

        // Bind methods
        this.init = this.init.bind(this);
        this.handleSessionStarted = this.handleSessionStarted.bind(this);
        this.handleSessionFinished = this.handleSessionFinished.bind(this);
        this.handleConnectionStatusChange = this.handleConnectionStatusChange.bind(this);

        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', this.init);
        } else {
            this.init();
        }
    }

    init() {
        if (this.isInitialized) return;

        // Only initialize on user view (not admin pages)
        if (!this.isUserView()) {
            return;
        }

        console.log('[UserRealtime] Initializing user real-time updates');

        // Create WebSocket service for users
        this.wsService = window.wsManager.createService('user', '/ws/user');

        // Set up event listeners
        this.setupEventListeners();

        // Create connection status indicator
        this.createConnectionStatusIndicator();

        // Monitor user interactions
        this.setupInteractionMonitoring();

        this.isInitialized = true;
    }

    isUserView() {
        // Check if we're on the user view (not admin)
        return !window.location.pathname.includes('/admin') &&
               (document.querySelector('.meme-container, #rating-slider, [data-page=\"user\"]') !== null ||
                document.querySelector('h2').textContent.includes('Rate This Meme'));
    }

    setupEventListeners() {
        if (!this.wsService) return;

        // Connection events
        this.wsService.addEventListener('connected', () => {
            console.log('[UserRealtime] WebSocket connected');
            this.updateConnectionStatus('connected');
        });

        this.wsService.addEventListener('disconnected', () => {
            console.log('[UserRealtime] WebSocket disconnected');
            this.updateConnectionStatus('disconnected');
        });

        this.wsService.addEventListener('status_changed', this.handleConnectionStatusChange);

        // Session events
        this.wsService.addEventListener('session_started', this.handleSessionStarted);
        this.wsService.addEventListener('session_finished', this.handleSessionFinished);
    }

    setupInteractionMonitoring() {
        // Monitor if user is currently rating a meme
        const ratingSlider = document.getElementById('rating-slider');
        const submitButton = document.getElementById('submit-rating');

        if (ratingSlider) {
            ratingSlider.addEventListener('input', () => {
                this.isRatingInProgress = true;

                // Reset after 30 seconds of inactivity
                clearTimeout(this.ratingTimeout);
                this.ratingTimeout = setTimeout(() => {
                    this.isRatingInProgress = false;
                }, 30000);
            });
        }

        if (submitButton) {
            submitButton.addEventListener('click', () => {
                this.isRatingInProgress = false;
                clearTimeout(this.ratingTimeout);
            });
        }
    }

    createConnectionStatusIndicator() {
        // Create a small connection status indicator in the corner
        this.connectionStatusElement = document.createElement('div');
        this.connectionStatusElement.id = 'user-connection-status';
        this.connectionStatusElement.className = 'fixed bottom-4 left-4 z-40 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1';

        document.body.appendChild(this.connectionStatusElement);
        this.updateConnectionStatus('connecting');
    }

    updateConnectionStatus(status) {
        if (!this.connectionStatusElement) return;

        // Remove existing status classes
        this.connectionStatusElement.className = 'fixed bottom-4 left-4 z-40 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1';

        let statusText, statusClass, statusIcon;

        switch (status) {
            case 'connected':
                statusText = 'Live';
                statusClass = 'bg-green-100 text-green-800';
                statusIcon = '🟢';
                break;
            case 'connecting':
            case 'reconnecting':
                statusText = 'Connecting';
                statusClass = 'bg-yellow-100 text-yellow-800';
                statusIcon = '🟡';
                break;
            case 'disconnected':
                statusText = 'Offline';
                statusClass = 'bg-red-100 text-red-800';
                statusIcon = '🔴';
                break;
            case 'error':
            case 'failed':
                statusText = 'Error';
                statusClass = 'bg-red-100 text-red-800';
                statusIcon = '❌';
                break;
            default:
                statusText = 'Unknown';
                statusClass = 'bg-gray-100 text-gray-800';
                statusIcon = '⚪';
        }

        this.connectionStatusElement.className += ` ${statusClass}`;
        this.connectionStatusElement.innerHTML = `${statusIcon} ${statusText}`;

        // Auto-hide after successful connection
        if (status === 'connected') {
            setTimeout(() => {
                if (this.connectionStatusElement) {
                    this.connectionStatusElement.style.opacity = '0.7';
                }
            }, 3000);
        }
    }

    handleConnectionStatusChange(data) {
        this.updateConnectionStatus(data.new_status);

        // Show subtle notification for connection issues
        if (data.new_status === 'disconnected') {
            this.showNotification('Connection lost - trying to reconnect...', 'warning');
        } else if (data.new_status === 'connected' && data.old_status !== 'connecting') {
            this.showNotification('Connection restored', 'success');
        }
    }

    handleSessionStarted(data) {
        console.log('[UserRealtime] Session started:', data);

        // Only refresh if user is not currently rating
        if (!this.isRatingInProgress) {
            this.showNotification('New session started! Loading fresh meme...', 'info');
            setTimeout(() => {
                this.refreshPage();
            }, 2000);
        } else {
            // Queue the refresh for when rating is complete
            this.queuedRefresh = true;
            this.showNotification('New session started! Will load after current rating.', 'info');
        }
    }

    handleSessionFinished(data) {
        console.log('[UserRealtime] Session finished:', data);

        this.showNotification('Session ended. Thank you for participating!', 'info');

        // Always refresh when session ends (show completion screen)
        setTimeout(() => {
            this.refreshPage();
        }, 3000);
    }

    showNotification(message, type = 'info') {
        // Use existing showMessage function if available
        if (typeof showMessage === 'function') {
            showMessage(message, type, 4000); // Shorter duration for user view
        } else {
            this.createToast(message, type);
        }
    }

    createToast(message, type) {
        // Create a toast notification optimized for mobile
        const toast = document.createElement('div');
        toast.className = `fixed top-4 left-1/2 transform -translate-x-1/2 z-50 px-4 py-2 rounded-lg shadow-lg text-white max-w-xs text-center`;

        switch (type) {
            case 'success':
                toast.className += ' bg-green-600';
                break;
            case 'warning':
                toast.className += ' bg-yellow-600';
                break;
            case 'error':
                toast.className += ' bg-red-600';
                break;
            default:
                toast.className += ' bg-blue-600';
        }

        toast.textContent = message;
        document.body.appendChild(toast);

        // Auto remove after 4 seconds
        setTimeout(() => {
            toast.remove();
        }, 4000);
    }

    refreshPage() {
        // Graceful page refresh for user view
        console.log('[UserRealtime] Refreshing page for session update');
        window.location.reload();
    }

    // Called when user completes a rating
    onRatingComplete() {
        this.isRatingInProgress = false;
        clearTimeout(this.ratingTimeout);

        // If there's a queued refresh, execute it now
        if (this.queuedRefresh) {
            this.queuedRefresh = false;
            setTimeout(() => {
                this.refreshPage();
            }, 1000);
        }
    }

    destroy() {
        if (this.wsService) {
            window.wsManager.destroyService('user');
            this.wsService = null;
        }

        if (this.connectionStatusElement) {
            this.connectionStatusElement.remove();
            this.connectionStatusElement = null;
        }

        clearTimeout(this.ratingTimeout);
        this.isInitialized = false;
    }
}

// Initialize user real-time manager
window.userRealtimeManager = new UserRealtimeManager();

// Hook into existing rating submission to notify real-time manager
document.addEventListener('DOMContentLoaded', function() {
    const submitButton = document.getElementById('submit-rating');
    if (submitButton && window.userRealtimeManager) {
        const originalClickHandler = submitButton.onclick;

        submitButton.addEventListener('click', function() {
            // Call original handler if it exists
            if (originalClickHandler) {
                originalClickHandler.call(this);
            }

            // Notify real-time manager
            setTimeout(() => {
                window.userRealtimeManager.onRatingComplete();
            }, 1000);
        });
    }
});
