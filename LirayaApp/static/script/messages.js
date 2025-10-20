// messages.js
// This script creates a smooth animation for alert messages and removes them after a delay

// Initialize when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Message alerts initialization
    const messages = document.querySelectorAll('.messages .alert');
    
    // If there are any messages, add a small delay to ensure they're visible first
    if (messages.length > 0) {
        // Wait a tiny bit to ensure CSS transitions are properly initialized
        setTimeout(() => {
            messages.forEach(function(message, index) {
                // Create staggered animation by adding slight delay for each message
                const delay = 3500 + (index * 200);
                
                setTimeout(function() {
                    // Force a repaint to ensure transition works properly
                    void message.offsetWidth;
                    
                    // Apply transform and opacity for a smooth fade-out and slide-up effect
                    message.style.opacity = '0';
                    message.style.transform = 'translateY(-20px)';
                    
                    // After the transition completes, hide the element
                    const handleTransitionEnd = function(e) {
                        // Remove this event listener to prevent multiple calls
                        message.removeEventListener('transitionend', handleTransitionEnd);
                        
                        // Completely hide the element
                        message.style.display = 'none';
                        
                        // Check if this is the last visible alert
                        const visibleAlerts = document.querySelectorAll('.messages .alert:not([style*="display: none"])');
                        if (visibleAlerts.length === 0) {
                            // If no more visible alerts, fade out the messages container too
                            const messagesContainer = document.querySelector('.messages');
                            if (messagesContainer) {
                                messagesContainer.style.opacity = '0';
                                // After container fades out, remove it from the document flow
                                setTimeout(() => {
                                    messagesContainer.style.display = 'none';
                                }, 700); // Match the CSS transition duration
                            }
                        }
                    };
                    
                    message.addEventListener('transitionend', handleTransitionEnd);
                }, delay);
            });
        }, 100); // Small delay to ensure everything is properly rendered
    }
});
