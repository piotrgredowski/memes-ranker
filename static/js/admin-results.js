/**
 * Admin Results Reveal JavaScript
 * Handles the interactive results reveal functionality
 */

class AdminResults {
    constructor() {
        this.sessionId = window.sessionId;
        this.results = window.results || [];
        this.revealStatus = window.initialRevealStatus || { current_position: 0, is_complete: false };
        this.totalPositions = window.totalPositions || 0;

        console.log('AdminResults initialized with:', {
            sessionId: this.sessionId,
            results: this.results,
            revealStatus: this.revealStatus,
            totalPositions: this.totalPositions
        });

        this.initializeElements();
        this.bindEvents();
        this.updateDisplay();
    }

    initializeElements() {
        this.nextBtn = document.getElementById('next-btn');
        this.prevBtn = document.getElementById('prev-btn');
        this.resetBtn = document.getElementById('reset-btn');
        this.progressBar = document.getElementById('progress-bar');
        this.currentReveal = document.getElementById('current-reveal');
        this.positionTitle = document.getElementById('position-title');
        this.positionDesc = document.getElementById('position-desc');
        this.memeImage = document.getElementById('current-meme-img');
        this.memeTitle = document.getElementById('current-meme-title');
        this.voteCount = document.getElementById('vote-count');
        this.avgScore = document.getElementById('avg-score');
        this.medianScore = document.getElementById('median-score');
        this.minScore = document.getElementById('min-score');
        this.maxScore = document.getElementById('max-score');
        this.stdDev = document.getElementById('std-dev');

        console.log('Elements initialized:', {
            nextBtn: this.nextBtn,
            prevBtn: this.prevBtn,
            resetBtn: this.resetBtn,
            progressBar: this.progressBar,
            currentReveal: this.currentReveal
        });
    }

    bindEvents() {
        console.log('Binding events to buttons:', {
            nextBtn: this.nextBtn,
            prevBtn: this.prevBtn,
            resetBtn: this.resetBtn
        });

        this.nextBtn?.addEventListener('click', () => {
            console.log('Next button clicked');
            this.revealNext();
        });
        this.prevBtn?.addEventListener('click', () => {
            console.log('Previous button clicked');
            this.revealPrevious();
        });
        this.resetBtn?.addEventListener('click', () => {
            console.log('Reset button clicked');
            this.resetReveal();
        });
    }

    async revealNext() {
        console.log('revealNext called, current position:', this.revealStatus.current_position, 'total:', this.totalPositions);

        if (this.revealStatus.current_position >= this.totalPositions) {
            console.log('Already at max position, returning');
            return;
        }

        try {
            this.setButtonsLoading(true);

            const url = `/admin/results/${this.sessionId}/next`;
            console.log('Making POST request to:', url);

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            console.log('Response status:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.revealStatus.current_position = data.position;
            this.revealStatus.is_complete = data.is_complete;

            this.updateDisplay();
            this.showMemeData(data.meme_data);

        } catch (error) {
            console.error('Error revealing next position:', error);
            this.showError('Failed to reveal next position. Please try again.');
        } finally {
            this.setButtonsLoading(false);
        }
    }

    async revealPrevious() {
        if (this.revealStatus.current_position <= 0) {
            return;
        }

        try {
            this.setButtonsLoading(true);

            const response = await fetch(`/admin/results/${this.sessionId}/previous`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.revealStatus.current_position = data.position;
            this.revealStatus.is_complete = false;

            this.updateDisplay();
            this.showCurrentPosition();

        } catch (error) {
            console.error('Error going to previous position:', error);
            this.showError('Failed to go to previous position. Please try again.');
        } finally {
            this.setButtonsLoading(false);
        }
    }

    async resetReveal() {
        console.log('Reset button clicked, showing confirmation dialog');

        const confirmed = confirm('Are you sure you want to reset the reveal? This will hide all revealed positions.');
        console.log('User confirmed reset:', confirmed);

        if (!confirmed) {
            console.log('User cancelled reset');
            return;
        }

        try {
            this.setButtonsLoading(true);

            const url = `/admin/results/${this.sessionId}/reset`;
            console.log('Making POST request to reset endpoint:', url);

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            console.log('Reset response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Reset request failed:', errorText);
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Reset response data:', data);

            this.revealStatus.current_position = 0;
            this.revealStatus.is_complete = false;

            console.log('Updating display after reset');
            this.updateDisplay();
            this.hideCurrentReveal();

        } catch (error) {
            console.error('Error resetting reveal:', error);
            this.showError('Failed to reset reveal. Please try again.');
        } finally {
            this.setButtonsLoading(false);
        }
    }

    updateDisplay() {
        console.log('Updating display with status:', this.revealStatus);

        // Update progress bar
        const progressPercent = this.totalPositions > 0 ?
            (this.revealStatus.current_position / this.totalPositions * 100) : 0;
        if (this.progressBar) {
            this.progressBar.style.width = `${progressPercent}%`;
            console.log('Updated progress bar to:', progressPercent + '%');
        }

        // Update progress text
        const progressText = document.getElementById('progress-text');
        if (progressText) {
            progressText.textContent = `${progressPercent.toFixed(1)}% Complete`;
        }

        // Update progress description
        const progressDesc = document.querySelector('.card-description');
        if (progressDesc) {
            progressDesc.textContent = `Position ${this.revealStatus.current_position} of ${this.totalPositions}`;
        }

        // Update button states
        if (this.nextBtn) {
            this.nextBtn.disabled = this.revealStatus.current_position >= this.totalPositions;
            console.log('Next button disabled:', this.nextBtn.disabled);
        }
        if (this.prevBtn) {
            this.prevBtn.disabled = this.revealStatus.current_position <= 0;
            console.log('Previous button disabled:', this.prevBtn.disabled);
        }

        // Update position display with proper place naming
        if (this.positionTitle) {
            if (this.revealStatus.current_position === 0) {
                this.positionTitle.textContent = 'Ready to Reveal';
            } else {
                const placeName = this.getPlaceName(this.revealStatus.current_position);
                console.log('Updating position title to:', placeName, 'for position:', this.revealStatus.current_position);
                this.positionTitle.textContent = placeName;
            }
        }
        if (this.positionDesc) {
            if (this.revealStatus.current_position === 0) {
                this.positionDesc.textContent = 'Click "Next" to start revealing results';
            } else if (this.revealStatus.is_complete) {
                this.positionDesc.textContent = 'All positions revealed!';
            } else {
                this.positionDesc.textContent = `Currently revealing...`;
            }
        }

        // Show/hide current reveal section - only show top 3 positions
        if (this.currentReveal) {
            const showPosition = this.revealStatus.current_position > 0 && this.revealStatus.current_position >= (this.totalPositions - 2);
            if (showPosition) {
                this.currentReveal.classList.remove('hidden');
                console.log('Showing current reveal section');
            } else {
                this.currentReveal.classList.add('hidden');
                console.log('Hiding current reveal section');
            }
        }
    }

    getPlaceName(position) {
        if (position === this.totalPositions) {
            return '1st Place';
        } else if (position === this.totalPositions - 1) {
            return '2nd Place';
        } else if (position === this.totalPositions - 2) {
            return '3rd Place';
        } else {
            return `Position ${position}`;
        }
    }

    showMemeData(memeData) {
        if (!memeData) {
            this.showCurrentPosition();
            return;
        }

        // Update meme image
        if (this.memeImage) {
            this.memeImage.src = memeData.path;
            this.memeImage.alt = memeData.filename;
        }

        // Update meme title
        if (this.memeTitle) {
            this.memeTitle.textContent = memeData.filename;
        }

        // Update individual stats elements
        if (this.voteCount) {
            this.voteCount.textContent = memeData.vote_count || 0;
        }
        if (this.avgScore) {
            this.avgScore.textContent = memeData.average_score ? memeData.average_score.toFixed(1) : '0.0';
        }
        if (this.medianScore) {
            this.medianScore.textContent = memeData.median_score ? memeData.median_score.toFixed(1) : '0.0';
        }
        if (this.minScore) {
            this.minScore.textContent = memeData.min_score !== undefined ? memeData.min_score : '0';
        }
        if (this.maxScore) {
            this.maxScore.textContent = memeData.max_score !== undefined ? memeData.max_score : '0';
        }
        if (this.stdDev) {
            this.stdDev.textContent = memeData.std_deviation ? memeData.std_deviation.toFixed(1) : '0.0';
        }
    }

    showCurrentPosition() {
        // Find the current position data from results
        const currentResult = this.results.find(r => r.position === this.revealStatus.current_position);
        if (currentResult) {
            this.showMemeData(currentResult);
        }
    }

    hideCurrentReveal() {
        if (this.currentReveal) {
            this.currentReveal.classList.add('hidden');
        }
    }

    setButtonsLoading(loading) {
        const buttons = [this.nextBtn, this.prevBtn, this.resetBtn];
        buttons.forEach(btn => {
            if (btn) {
                btn.disabled = loading;
                if (loading) {
                    btn.classList.add('opacity-50', 'cursor-not-allowed');
                    btn.textContent = 'Loading...';
                } else {
                    btn.classList.remove('opacity-50', 'cursor-not-allowed');
                    // Restore original text
                    if (btn === this.nextBtn) btn.innerHTML = 'Next <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>';
                    if (btn === this.prevBtn) btn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg> Previous';
                    if (btn === this.resetBtn) btn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg> Reset';
                }
            }
        });
    }

    showError(message) {
        // Create a simple error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50';
        errorDiv.textContent = message;

        document.body.appendChild(errorDiv);

        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing AdminResults...');
    console.log('Available variables:', {
        sessionId: window.sessionId,
        results: window.results,
        initialRevealStatus: window.initialRevealStatus,
        totalPositions: window.totalPositions
    });

    try {
        new AdminResults();
    } catch (error) {
        console.error('Error initializing AdminResults:', error);
    }
});
