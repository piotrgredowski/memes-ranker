// Main application JavaScript for memes-ranker

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Main initialization function
function initializeApp() {
    // Initialize sliders
    initializeSliders();

    // Initialize form handlers
    initializeFormHandlers();

    // Initialize keyboard navigation
    initializeKeyboardNavigation();

    // Initialize accessibility features
    initializeAccessibility();

    // Initialize QR code widget
    initializeQRWidget();
}

// Slider component functionality
function initializeSliders() {
    const sliders = document.querySelectorAll('input[type="range"]');

    sliders.forEach(slider => {
        // Create visual slider track
        const track = document.createElement('div');
        track.className = 'slider-track';

        const range = document.createElement('div');
        range.className = 'slider-range';

        const thumb = document.createElement('div');
        thumb.className = 'slider-thumb';

        // Update visual appearance
        function updateSlider() {
            const value = slider.value;
            const max = slider.max;
            const percentage = (value / max) * 100;

            range.style.width = percentage + '%';
            thumb.style.left = percentage + '%';

            // Update ARIA attributes
            slider.setAttribute('aria-valuenow', value);
            slider.setAttribute('aria-valuetext', `${value} out of ${max}`);
        }

        slider.addEventListener('input', updateSlider);
        slider.addEventListener('change', updateSlider);

        // Initialize
        updateSlider();
    });
}

// Form handling
function initializeFormHandlers() {
    // Generic form submission handler
    const forms = document.querySelectorAll('form');

    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = form.querySelector('button[type="submit"]');

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Processing...';

                // Re-enable after 5 seconds as fallback
                setTimeout(() => {
                    submitButton.disabled = false;
                    submitButton.textContent = submitButton.dataset.originalText || 'Submit';
                }, 5000);
            }
        });
    });
}

// Keyboard navigation
function initializeKeyboardNavigation() {
    // Arrow key navigation for rating
    const ratingSlider = document.getElementById('rating-slider');
    const submitButton = document.getElementById('submit-rating');

    if (ratingSlider) {
        ratingSlider.addEventListener('keydown', function(e) {
            switch (e.key) {
                case 'Enter':
                case ' ':
                    e.preventDefault();
                    if (submitButton) {
                        submitButton.click();
                    }
                    break;
                case 'ArrowLeft':
                case 'ArrowDown':
                    e.preventDefault();
                    const newValueDown = Math.max(0, parseInt(this.value) - 1);
                    this.value = newValueDown;
                    this.dispatchEvent(new Event('input'));
                    break;
                case 'ArrowRight':
                case 'ArrowUp':
                    e.preventDefault();
                    const newValueUp = Math.min(10, parseInt(this.value) + 1);
                    this.value = newValueUp;
                    this.dispatchEvent(new Event('input'));
                    break;
                case 'Home':
                    e.preventDefault();
                    this.value = 0;
                    this.dispatchEvent(new Event('input'));
                    break;
                case 'End':
                    e.preventDefault();
                    this.value = 10;
                    this.dispatchEvent(new Event('input'));
                    break;
            }
        });
    }

    // Dialog keyboard handling
    const dialogs = document.querySelectorAll('.dialog-overlay');

    dialogs.forEach(dialog => {
        dialog.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeDialog(dialog);
            }
        });
    });
}

// Accessibility features
function initializeAccessibility() {
    // Focus management for dialogs
    const dialogs = document.querySelectorAll('.dialog-overlay');

    dialogs.forEach(dialog => {
        // Store the element that opened the dialog
        dialog.addEventListener('show', function() {
            dialog.dataset.previousFocus = document.activeElement;

            // Focus first focusable element in dialog
            const firstFocusable = dialog.querySelector('input, button, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (firstFocusable) {
                firstFocusable.focus();
            }
        });

        dialog.addEventListener('hide', function() {
            // Return focus to previous element
            const previousFocus = document.querySelector(dialog.dataset.previousFocus);
            if (previousFocus) {
                previousFocus.focus();
            }
        });
    });

    // Announce dynamic content changes
    const announcer = document.createElement('div');
    announcer.setAttribute('aria-live', 'polite');
    announcer.setAttribute('aria-atomic', 'true');
    announcer.className = 'sr-only';
    announcer.id = 'announcer';
    document.body.appendChild(announcer);

    // Add announcement function to global scope
    window.announce = function(message) {
        announcer.textContent = message;
        setTimeout(() => {
            announcer.textContent = '';
        }, 1000);
    };
}

// Dialog utilities
function closeDialog(dialog) {
    dialog.classList.add('hidden');
    dialog.dispatchEvent(new Event('hide'));
}

function openDialog(dialog) {
    dialog.classList.remove('hidden');
    dialog.dispatchEvent(new Event('show'));
}

// API utilities
async function apiCall(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const finalOptions = { ...defaultOptions, ...options };

    // Add auth token if available
    const token = getCookie('admin_token');
    if (token) {
        finalOptions.headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, finalOptions);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Cookie utilities
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

function setCookie(name, value, days = 30) {
    const expires = new Date();
    expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
    document.cookie = `${name}=${value}; expires=${expires.toUTCString()}; path=/`;
}

// Message display utilities
function showMessage(message, type = 'info', duration = 5000) {
    const container = document.getElementById('message-container') || createMessageContainer();

    const messageDiv = document.createElement('div');
    messageDiv.className = `card p-4 mb-4 message-${type}`;

    // Apply styling based on type
    switch (type) {
        case 'success':
            messageDiv.classList.add('bg-green-100', 'text-green-800', 'border-green-200');
            break;
        case 'error':
            messageDiv.classList.add('bg-red-100', 'text-red-800', 'border-red-200');
            break;
        case 'warning':
            messageDiv.classList.add('bg-yellow-100', 'text-yellow-800', 'border-yellow-200');
            break;
        default:
            messageDiv.classList.add('bg-blue-100', 'text-blue-800', 'border-blue-200');
    }

    messageDiv.textContent = message;
    container.appendChild(messageDiv);

    // Auto-remove message
    setTimeout(() => {
        messageDiv.remove();
    }, duration);

    // Announce to screen readers
    if (window.announce) {
        window.announce(message);
    }
}

function createMessageContainer() {
    const container = document.createElement('div');
    container.id = 'message-container';
    container.className = 'fixed top-4 right-4 z-50 max-w-md';
    document.body.appendChild(container);
    return container;
}

// Loading state utilities
function setLoadingState(element, isLoading = true) {
    if (isLoading) {
        element.disabled = true;
        element.dataset.originalText = element.textContent;
        element.textContent = 'Loading...';
        element.classList.add('loading');
    } else {
        element.disabled = false;
        element.textContent = element.dataset.originalText || 'Submit';
        element.classList.remove('loading');
    }
}

// Progressive enhancement for forms
function enhanceForm(form) {
    const submitButton = form.querySelector('button[type="submit"]');

    form.addEventListener('submit', function(e) {
        if (submitButton) {
            setLoadingState(submitButton, true);
        }
    });
}

// QR Code Widget functionality
function initializeQRWidget() {
    const qrWidget = document.getElementById('qr-widget');
    if (!qrWidget) return;

    const toggle = qrWidget.querySelector('.qr-widget-toggle');
    const panel = qrWidget.querySelector('.qr-widget-panel');
    const closeButton = qrWidget.querySelector('.qr-widget-close');
    let isOpen = false;

    // Toggle function
    function toggleQRWidget() {
        isOpen = !isOpen;
        if (isOpen) {
            panel.classList.add('visible');
            toggle.setAttribute('aria-expanded', 'true');
            toggle.setAttribute('aria-label', 'Close QR code');
            // Focus close button for accessibility
            closeButton.focus();
        } else {
            panel.classList.remove('visible');
            toggle.setAttribute('aria-expanded', 'false');
            toggle.setAttribute('aria-label', 'Show QR code');
            // Return focus to toggle button
            toggle.focus();
        }
    }

    // Close function
    function closeQRWidget() {
        if (isOpen) {
            toggleQRWidget();
        }
    }

    // Event listeners
    toggle.addEventListener('click', toggleQRWidget);
    closeButton.addEventListener('click', closeQRWidget);

    // Close on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && isOpen) {
            closeQRWidget();
        }
    });

    // Close when clicking outside
    document.addEventListener('click', function(e) {
        if (isOpen && !qrWidget.contains(e.target)) {
            closeQRWidget();
        }
    });

    // Initialize ARIA attributes
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Show QR code');
    toggle.setAttribute('aria-describedby', 'qr-widget-description');
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-labelledby', 'qr-widget-title');
}

// Export utilities for use in other scripts
window.memesRanker = {
    apiCall,
    getCookie,
    setCookie,
    showMessage,
    setLoadingState,
    enhanceForm,
    closeDialog,
    openDialog
};
