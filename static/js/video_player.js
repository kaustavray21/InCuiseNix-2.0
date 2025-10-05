document.addEventListener('DOMContentLoaded', function() {
    // Check if the player element exists on the page
    const playerElement = document.getElementById('player');
    if (!playerElement) return;

    // Initialize the Plyr player with a definitive set of controls
    const player = new Plyr('#player', {
        // This list explicitly defines which buttons appear in the player's control bar.
        controls: [
            'play-large',   // The big play button in the middle
            'play',         // The play button in the control bar
            'progress',     // The video progress bar
            'current-time', // The current time display
            'mute',
            'volume',
            'captions',     // This explicitly adds the main caption (CC) button
            'settings',     // The settings menu (gear icon)
            'fullscreen'
        ],
        // This ensures the captions toggle is available inside the settings menu as well
        settings: ['captions', 'speed', 'loop'],
        youtube: {
            rel: 0, // Hides the grid of related videos when the video ends.
            cc_load_policy: 1,
            noCookie: true,
        }
    });

    // Make the player instance available globally so notes.js can access it
    window.videoPlayer = player;

    // --- START: New Transcript Interactivity Code ---
    const transcriptContainer = document.getElementById('transcript-container');

    if (transcriptContainer && window.videoPlayer) {
        transcriptContainer.addEventListener('click', function(event) {
            const line = event.target.closest('.transcript-line');
            if (line) {
                const startTime = parseFloat(line.dataset.start);
                if (!isNaN(startTime)) {
                    window.videoPlayer.currentTime = startTime;
                    window.videoPlayer.play(); // Optional: auto-play when a line is clicked
                }
            }
        });
    }
    // --- END: New Transcript Interactivity Code ---
});