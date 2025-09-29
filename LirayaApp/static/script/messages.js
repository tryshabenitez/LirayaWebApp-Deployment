// messages_in_admins.js
// This script hides the .messages container after a delay and removes its space completely.

document.addEventListener('DOMContentLoaded', function() {
    var messages = document.querySelector('.messages');
    if (messages) {
        setTimeout(function() {
            messages.style.display = 'none'; // Remove all space
        }, 3500); // Adjust delay as needed (ms)
    }
});
