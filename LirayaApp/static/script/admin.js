//////////////////// MESSAGE FUNCTIONS ////////////////////
document.addEventListener('DOMContentLoaded', function() {
    const messages = document.querySelectorAll('.messages .alert');
    
    messages.forEach(function(message) {
        // Add a timeout to fade out and remove the message
        setTimeout(function() {
            // Apply fade-out effect
            message.style.transition = 'opacity 0.5s ease-out'; // Smooth fade-out transition
            message.style.opacity = '0'; // Fade out the message

            // Wait for the transition to end before removing the element from the document flow
            message.addEventListener('transitionend', function() {
                message.style.transition = 'none';  // Disable transition after fade out
                message.style.display = 'none';  // Completely remove the element from the layout, no space left
            });
        }, 5000);  // Hide after 5 seconds
    });
});

//////////////////// PROFILE FUNCTIONS admin_profile.html ////////////////////


//// CHANGE PASSWORD ////
// Show password fields and change the button to "Cancel" when "Change Password" is clicked
document.getElementById('change-password-btn').addEventListener('click', function() {
    // Check if the button text is "Change Password"
    if (document.getElementById('change-password-btn').textContent === 'Change Password') {
        // Show the password fields and save button
        document.getElementById('password-fields').style.display = 'block';
        document.getElementById('save-btn-pass').style.display = 'inline-block'; // or 'block' depending on your design
        clearFields();
        // Change the "Change Password" button text to "Cancel"
        document.getElementById('change-password-btn').textContent = 'Cancel';
    } else {
        // If the text is "Cancel", hide the password fields and save button
        clearFields();
        document.getElementById('password-fields').style.display = 'none';
        document.getElementById('save-btn-pass').style.display = 'none';
       

        // Change the button text back to "Change Password"
        document.getElementById('change-password-btn').textContent = 'Change Password';
    }
});

// Hide password fields and save button when clicking "Save"
document.getElementById('save-btn-pass').addEventListener('click', function() {
    // Hide the password fields and save button
    document.getElementById('password-fields').style.display = 'none';
    document.getElementById('save-btn-pass').style.display = 'none';

    // Change the "Cancel" button text back to "Change Password"
    document.getElementById('change-password-btn').textContent = 'Change Password';
});


function togglePassword(passwordFieldId) {
    var passwordField = document.getElementById(passwordFieldId);
    var eyeIcon = document.getElementById('eye-icon-' + passwordFieldId);
    
    if (passwordField.type === "password") {
        passwordField.type = "text";
        eyeIcon.src = showPasswordIcon;  // Change the eye icon to open
    } else {
        passwordField.type = "password";
        eyeIcon.src = hidePasswordIcon;  // Change the eye icon to closed
    }
}


//// CHANGE PROFILE PICTURE ////
// Trigger file input when 'Upload' button is clicked
document.getElementById('upload-button').addEventListener('click', function() {
    document.getElementById('profile-picture-upload').click();
});

// Open the cropping modal when a new file is selected
document.getElementById('profile-picture-upload').addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function() {
            const imageUrl = reader.result;

            // Set the image URL to the cropper modal
            const cropperImage = document.getElementById('cropper-image');
            cropperImage.src = imageUrl;

            // Show the cropping modal
            document.getElementById('cropper-modal').style.display = 'block';

            // Initialize Cropper.js
            const cropper = new Cropper(cropperImage, {
                aspectRatio: 1, // You can set a fixed aspect ratio if needed
                viewMode: 1, // Restricts the image to the container size
                ready() {
                    console.log('Cropper is ready');
                }
            });

            // Handle save crop action
            document.getElementById('crop-save').addEventListener('click', function() {
                // Get the cropped image data
                const croppedCanvas = cropper.getCroppedCanvas();

                // Convert the canvas image to a base64 string
                const croppedImageUrl = croppedCanvas.toDataURL('image/jpeg');

                // Set the base64 image data in the hidden input field
                document.getElementById('cropped-image-data').value = croppedImageUrl;

                // Update the profile preview with the cropped image
                const previewImage = document.getElementById('profile-preview');
                previewImage.src = croppedImageUrl;

                // Close the modal
                document.getElementById('cropper-modal').style.display = 'none';

                // Destroy cropper to release resources
                cropper.destroy();
            });
        };
        reader.readAsDataURL(file);
    }
});


//// CHANGE PROFILE INFORMATION ////
document.addEventListener('DOMContentLoaded', function() {
    // Initially, make all fields read-only except the gender dropdown (disabled)
    toggleFields(true);

    // "Edit" button functionality
    document.getElementById('edit-btn').addEventListener('click', function() {
        // Check if the button text is "Edit"
        if (this.textContent === 'Edit') {
            // Change button text to "Cancel"
            this.textContent = 'Cancel';

            // Show the Save button
            document.getElementById('save-btn').style.display = 'inline-block';

            // Enable fields and gender dropdown
            toggleFields(false);
            document.getElementById('gender').disabled = false;  // Enable the gender dropdown
        } else {
            // If the text is "Cancel", revert to original "Edit" state
            this.textContent = 'Edit';
            location.reload();

            // Hide the Save button
            document.getElementById('save-btn').style.display = 'none';

            // Make fields read-only again and disable gender dropdown
            toggleFields(true);
            document.getElementById('gender').disabled = true; // Disable the gender dropdown
        }
    });

    // "Save" button functionality
    document.getElementById('save-btn').addEventListener('click', function() {

            // Get the gender from the dropdown
        const selectedGender = document.getElementById('gender').value;

        // Set the value of the hidden input
        document.getElementById('gender-hidden').value = selectedGender;

        // Hide the Save button
        document.getElementById('save-btn').style.display = 'none';

        // Reset button text to "Edit"
        document.getElementById('edit-btn').textContent = 'Edit';

        // Make fields read-only again and disable gender dropdown
        toggleFields(true);
        document.getElementById('gender').disabled = true; // Disable the gender dropdown

    
    });
});

// Function to toggle fields between read-only/disabled and editable
function toggleFields(isDisabled) {
    const fields = document.querySelectorAll('.admin-input-field');
    fields.forEach(function(field) {
        field.readOnly = isDisabled; // Set readonly for text inputs
    });
}

/// zip code and contact number /// 
document.getElementById('zipcode').addEventListener('input', function() {
    // Get the current value of the input field
    let zipcode = this.value;

    // Remove any non-numeric characters
    zipcode = zipcode.replace(/\D/g, '');

    // Ensure the input is limited to 4 digits
    if (zipcode.length > 4) {
        zipcode = zipcode.slice(0, 4);  // Limit to 4 digits
    }

    // Update the input field value with the cleaned zipcode
    this.value = zipcode;
});

document.getElementById('contact-number').addEventListener('input', function() {
    // Get the current value of the input field
    let contactNumber = this.value;

    // Remove any non-numeric characters
    contactNumber = contactNumber.replace(/\D/g, '');

    // Ensure the input starts with '09' and is limited to 11 digits
    if (contactNumber.length > 11) {
        contactNumber = contactNumber.slice(0, 11);  // Limit to 11 digits
    }

    // Ensure it starts with '09'
    if (!contactNumber.startsWith('09')) {
        contactNumber = '09' + contactNumber.slice(2);  // Force '09' at the beginning
    }

    // Update the input field value with the cleaned contact number
    this.value = contactNumber;
});

//// BIRTHDATE ////
document.getElementById('birthdate').addEventListener('change', function() {
    var birthdate = new Date(this.value);
    var today = new Date();
    var age = today.getFullYear() - birthdate.getFullYear();
    var month = today.getMonth() - birthdate.getMonth();
    
    // If the user hasn't had their birthday yet this year
    if (month < 0 || (month === 0 && today.getDate() < birthdate.getDate())) {
        age--;
    }

    if (age < 18 || age > 80) {
        alert("You must be between 18 and 80 years old.");
        this.value = '';  // Clear invalid birthdate input
    }
});


//// CLEAR FIELDS ////
// Function to clear the fields (empty the values)
function clearFields() {
    const passwordFields = document.querySelectorAll('#password-fields input');
    passwordFields.forEach(function(field) {
        field.value = ''; // Clear the value of each input field
    });
}

