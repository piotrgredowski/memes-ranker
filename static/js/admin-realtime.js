/**
 * Admin Dashboard Real-time Updates
 * Handles WebSocket connections and UI updates for the admin dashboard
 */

class AdminRealtimeManager {
    constructor() {
        this.wsService = null;
        this.isInitialized = false;
        this.connectionStatusElement = null;

        // Bind methods
        this.init = this.init.bind(this);
        this.handleSessionCreated = this.handleSessionCreated.bind(this);
        this.handleSessionStarted = this.handleSessionStarted.bind(this);
        this.handleSessionFinished = this.handleSessionFinished.bind(this);
        this.handleMemesPopulated = this.handleMemesPopulated.bind(this);
        this.handleNewRating = this.handleNewRating.bind(this);
        this.handleStatsUpdated = this.handleStatsUpdated.bind(this);
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

        // Only initialize on admin dashboard page
        if (!this.isAdminDashboard()) {
            return;
        }

        console.log('[AdminRealtime] Initializing admin real-time updates');

        // Create WebSocket service for admin
        this.wsService = window.wsManager.createService('admin', '/ws/admin');

        // Set up event listeners
        this.setupEventListeners();

        // Create connection status indicator
        this.createConnectionStatusIndicator();

        this.isInitialized = true;
    }

    isAdminDashboard() {
        // Check if we're on the admin dashboard page
        return window.location.pathname.includes('/admin') &&
               document.querySelector('.admin-dashboard, #admin-dashboard, [data-page=\"admin\"]') !== null ||
               document.querySelector('h1').textContent.includes('Admin Dashboard');
    }

    setupEventListeners() {
        if (!this.wsService) return;

        // Connection events
        this.wsService.addEventListener('connected', () => {
            console.log('[AdminRealtime] WebSocket connected');
            this.updateConnectionStatus('connected');
        });

        this.wsService.addEventListener('disconnected', () => {
            console.log('[AdminRealtime] WebSocket disconnected');
            this.updateConnectionStatus('disconnected');
        });

        this.wsService.addEventListener('status_changed', this.handleConnectionStatusChange);

        // Session events
        this.wsService.addEventListener('session_created', this.handleSessionCreated);
        this.wsService.addEventListener('session_started', this.handleSessionStarted);
        this.wsService.addEventListener('session_finished', this.handleSessionFinished);

        // Meme events
        this.wsService.addEventListener('memes_populated', this.handleMemesPopulated);

        // Rating events
        this.wsService.addEventListener('new_rating', this.handleNewRating);
        this.wsService.addEventListener('stats_updated', this.handleStatsUpdated);
    }

    createConnectionStatusIndicator() {
        // Create connection status indicator
        const header = document.querySelector('.admin-dashboard h1, h1');
        if (header) {
            this.connectionStatusElement = document.createElement('div');
            this.connectionStatusElement.id = 'connection-status';
            this.connectionStatusElement.className = 'inline-flex items-center gap-2 ml-4 px-3 py-1 rounded-full text-sm font-medium';

            header.appendChild(this.connectionStatusElement);
            this.updateConnectionStatus('connecting');
        }
    }

    updateConnectionStatus(status) {
        if (!this.connectionStatusElement) return;

        // Remove existing status classes
        this.connectionStatusElement.className = 'inline-flex items-center gap-2 ml-4 px-3 py-1 rounded-full text-sm font-medium';

        let statusText, statusClass, statusIcon;

        switch (status) {
            case 'connected':
                statusText = 'Live';
                statusClass = 'bg-green-100 text-green-800';
                statusIcon = '🟢';
                break;
            case 'connecting':
            case 'reconnecting':
                statusText = 'Connecting...';
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
    }

    handleConnectionStatusChange(data) {
        this.updateConnectionStatus(data.new_status);

        // Show toast notification for connection changes
        if (data.new_status === 'connected') {
            this.showNotification('Real-time updates connected', 'success');
        } else if (data.new_status === 'disconnected') {
            this.showNotification('Real-time updates disconnected', 'warning');
        }
    }

    handleSessionCreated(data) {
        console.log('[AdminRealtime] Session created:', data);
        this.showNotification(`New session created: ${data.name}`, 'info');

        // Refresh session info after a short delay
        setTimeout(() => {
            this.refreshPage();
        }, 1000);
    }

    handleSessionStarted(data) {
        console.log('[AdminRealtime] Session started:', data);
        this.showNotification(`Session started: ${data.name}`, 'success');

        // Update session info section
        this.updateSessionInfo(data);
    }

    handleSessionFinished(data) {
        console.log('[AdminRealtime] Session finished:', data);
        this.showNotification(`Session finished: ${data.name}`, 'info');

        // Refresh page to show updated state
        setTimeout(() => {
            this.refreshPage();
        }, 1000);
    }

    handleMemesPopulated(data) {
        console.log('[AdminRealtime] Memes populated:', data);
        this.showNotification(`${data.meme_count} memes added successfully!`, 'success');

        // Refresh meme statistics section
        setTimeout(() => {
            this.refreshPage();
        }, 1000);
    }

    handleNewRating(data) {
        console.log('[AdminRealtime] New rating:', data);

        // Update stats counters
        this.updateStatsCounters();
    }

    handleStatsUpdated(data) {
        console.log('[AdminRealtime] Stats updated:', data);

        // Update statistics display
        this.updateStatsDisplay(data.meme_stats);
    }

    updateSessionInfo(sessionData) {
        // Update active session display
        const sessionNameElement = document.querySelector('[data-session-name]');
        const sessionTimeElement = document.querySelector('[data-session-time]');

        if (sessionNameElement) {
            sessionNameElement.textContent = sessionData.name;
        }

        if (sessionTimeElement) {
            sessionTimeElement.textContent = sessionData.start_time || 'Just started';
        }

        // Show session section if it was hidden
        const sessionSection = document.querySelector('.session-info, [data-section=\"session\"]');
        if (sessionSection) {
            sessionSection.style.display = 'block';
        }
    }

    updateStatsCounters() {
        // Find and update stats counter elements
        const totalRatingsElement = document.querySelector('[data-stat=\"total-ratings\"]');
        if (totalRatingsElement) {
            const currentValue = parseInt(totalRatingsElement.textContent) || 0;
            totalRatingsElement.textContent = currentValue + 1;

            // Add visual feedback
            totalRatingsElement.classList.add('animate-pulse');
            setTimeout(() => {
                totalRatingsElement.classList.remove('animate-pulse');
            }, 1000);
        }
    }

    updateStatsDisplay(memeStats) {
        // This could be enhanced to update individual meme stats
        // For now, we'll just refresh the page for complete accuracy
        setTimeout(() => {
            this.refreshPage();
        }, 2000);
    }

    showNotification(message, type = 'info') {
        // Use existing showMessage function if available, or create toast
        if (typeof showMessage === 'function') {
            showMessage(message, type);
        } else {
            this.createToast(message, type);
        }
    }

    createToast(message, type) {
        // Create a simple toast notification
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 z-50 px-4 py-2 rounded-lg shadow-lg text-white max-w-sm`;

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

        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    refreshPage() {
        // Graceful page refresh - only if no user is currently interacting
        if (!document.hasFocus() || !this.isUserInteracting()) {
            window.location.reload();
        }
    }

    isUserInteracting() {
        // Check if user is currently interacting with forms or inputs
        const activeElement = document.activeElement;
        return activeElement && (
            activeElement.tagName === 'INPUT' ||
            activeElement.tagName === 'TEXTAREA' ||
            activeElement.tagName === 'SELECT' ||
            activeElement.isContentEditable
        );
    }

    destroy() {
        if (this.wsService) {
            window.wsManager.destroyService('admin');
            this.wsService = null;
        }

        if (this.connectionStatusElement) {
            this.connectionStatusElement.remove();
            this.connectionStatusElement = null;
        }

        this.isInitialized = false;
    }
}

// Initialize admin real-time manager
window.adminRealtimeManager = new AdminRealtimeManager();
