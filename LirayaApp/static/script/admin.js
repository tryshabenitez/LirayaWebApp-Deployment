//////////////////// MAIN INITIALIZATION ////////////////////
document.addEventListener('DOMContentLoaded', function() {
    

    // Password change initialization
    const changePasswordBtn = document.getElementById('change-password-btn');
    const passwordModal = document.getElementById('password-change-modal');
    const cancelPasswordBtn = document.getElementById('cancel-password-change');
    const passwordForm = document.getElementById('password-change-form');

    // Initialize password change functionality
    if (changePasswordBtn && passwordModal && cancelPasswordBtn && passwordForm) {
        changePasswordBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            passwordModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        });

        cancelPasswordBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            passwordModal.style.display = 'none';
            document.body.style.overflow = 'auto';
            passwordForm.reset();
        });

        passwordModal.addEventListener('click', function(e) {
            if (e.target === this) {
                e.stopPropagation();
                this.style.display = 'none';
                document.body.style.overflow = 'auto';
                passwordForm.reset();
            }
        });

        passwordForm.addEventListener('submit', function(e) {
            e.stopPropagation();
            const newPassword = document.getElementById('new-password').value;
            const confirmPassword = document.getElementById('confirm-password').value;
            
            if (newPassword !== confirmPassword) {
                e.preventDefault();
                alert('New password and confirm password do not match!');
            }
        });
    }

    // Profile editing initialization
    const editBtn = document.getElementById('edit-btn');
    const saveBtn = document.getElementById('save-btn');
    const genderSelect = document.getElementById('gender');

    if (editBtn && saveBtn && genderSelect) {
        toggleFields(true);  // Initially, make all fields read-only

        editBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            
            // Don't proceed if password modal is open
            if (passwordModal && passwordModal.style.display === 'flex') {
                return;
            }

            if (this.textContent === 'Edit') {
                this.textContent = 'Cancel';
                saveBtn.style.display = 'inline-block';
                toggleFields(false);
                genderSelect.disabled = false;
            } else {
                this.textContent = 'Edit';
                location.reload();
                saveBtn.style.display = 'none';
                toggleFields(true);
                genderSelect.disabled = true;
            }
        });

        saveBtn.addEventListener('click', function() {
            genderSelect.value && (document.getElementById('gender-hidden').value = genderSelect.value);
            this.style.display = 'none';
            editBtn.textContent = 'Edit';
            toggleFields(true);
            genderSelect.disabled = true;
        });
    }
    
    // Zipcode field validation
    const zipcodeField = document.getElementById('zipcode');
    if (zipcodeField) {
        zipcodeField.addEventListener('input', function() {
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
    }

    // Contact number field validation
    const contactNumberField = document.getElementById('contact-number');
    if (contactNumberField) {
        contactNumberField.addEventListener('input', function() {
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
    }

    // Birthdate field validation
    const birthdateField = document.getElementById('birthdate');
    if (birthdateField) {
        birthdateField.addEventListener('change', function() {
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
    }

    // Initialize form validation
    initFormValidation();
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




//// CHANGE PROFILE INFORMATION ////
// The profile editing functionality is now handled in the DOMContentLoaded section above

// Function to toggle fields between read-only/disabled and editable
function toggleFields(isDisabled) {
    const fields = document.querySelectorAll('.admin-input-field');
    fields.forEach(function(field) {
        field.readOnly = isDisabled; // Set readonly for text inputs
    });
}

// Zip code, contact number, and birthdate validations moved into DOMContentLoaded event



//// CLEAR FIELDS ////
// Function to clear the fields (empty the values)
function clearFields() {
    const passwordFields = document.querySelectorAll('#password-fields input');
    passwordFields.forEach(function(field) {
        field.value = ''; // Clear the value of each input field
    });
}


//// FORM VALIDATION FOR PROFILE EDITING ////
function initFormValidation() {
    // Helper to show error
    function showError(inputId, message) {
        let errorDiv = document.getElementById(inputId + '_error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'field-error';
            errorDiv.id = inputId + '_error';
            document.getElementById(inputId).insertAdjacentElement('afterend', errorDiv);
        }
        errorDiv.textContent = message;
        updateSaveButtonState(); // Update save button state when showing error
    }
    // Helper to clear error
    function clearError(inputId) {
        let errorDiv = document.getElementById(inputId + '_error');
        if (errorDiv) errorDiv.textContent = '';
        updateSaveButtonState(); // Update save button state when clearing error
    }
    
    // Function to check if there are any validation errors
    function hasValidationErrors() {
        const errorDivs = document.querySelectorAll('.field-error');
        for (const errorDiv of errorDivs) {
            if (errorDiv.textContent.trim()) {
                return true;
            }
        }
        return false;
    }

    // Function to update save button state
    function updateSaveButtonState() {
        const saveButton = document.getElementById('save-btn');
        if (saveButton) {
            const hasErrors = hasValidationErrors();
            saveButton.disabled = hasErrors;
            saveButton.style.opacity = hasErrors ? '0.5' : '1';
            saveButton.style.cursor = hasErrors ? 'not-allowed' : 'pointer';
        }
    }
    // Validation rules
    function validateNotEmpty(inputId, label) {
        const value = document.getElementById(inputId).value.trim();
        if (!value) {
            showError(inputId, label + ' cannot be blank');
            return false;
        } else {
            clearError(inputId);
            return true;
        }
    }
    // Additional validation rules for special fields
    function validateZipcode() {
        const input = document.getElementById('zipcode');
        const value = input.value.trim();
        if (!/^\d{4}$/.test(value) || parseInt(value) < 100 || parseInt(value) > 9811) {
            showError('zipcode', 'Invalid Zipcode. It should be a 4-digit number between 0100 and 9811.');
            return false;
        } else {
            clearError('zipcode');
            return true;
        }
    }
    function validateContactNumber() {
        const input = document.getElementById('contact-number');
        const value = input.value.trim();
        if (!value) {
            showError('contact-number', 'Contact number is required.');
            return false;
        }
        if (!/^09\d{9}$/.test(value)) {
            showError('contact-number', "Invalid contact number. It must be 11 digits and start with '09'.");
            return false;
        }
        clearError('contact-number');
        return true;
    }
    function validateEmail() {
        const input = document.getElementById('email');
        const value = input.value.trim();
        // Simple email regex
        if (!/^\S+@\S+\.\S+$/.test(value)) {
            showError('email', 'Invalid email address.');
            return false;
        }
        clearError('email');
        return true;
    }
    function validateState() {
        const input = document.getElementById('state');
        const value = input.value.trim();
        if (!value) {
            showError('state', 'State cannot be blank.');
            return false;
        }
        if (/\d/.test(value)) {
            showError('state', 'State must be a valid string and cannot contain numbers.');
            return false;
        }
        clearError('state');
        return true;
    }
    function validateBirthdate() {
        const input = document.getElementById('birthdate');
        const value = input.value;
        if (!value) {
            showError('birthdate', 'Birthdate is required.');
            return false;
        }
        const birthDate = new Date(value);
        const today = new Date();
        let age = today.getFullYear() - birthDate.getFullYear();
        const m = today.getMonth() - birthDate.getMonth();
        if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
            age--;
        }
        if (isNaN(age)) {
            showError('birthdate', 'Invalid birthdate format. Please use YYYY-MM-DD.');
            return false;
        }
        if (age < 18) {
            showError('birthdate', 'You must be at least 18 years old to register.');
            return false;
        }
        if (age > 80) {
            showError('birthdate', 'You must be 80 years old or younger to register.');
            return false;
        }
        clearError('birthdate');
        return true;
    }
    function validateGender() {
        const input = document.getElementById('gender');
        const value = input.value;
        if (!value || !['Male', 'Female', 'Other'].includes(value)) {
            showError('gender', 'Please select a valid gender.');
            return false;
        }
        clearError('gender');
        return true;
    }
    // Username validation with caching and improved status handling
    let lastCheckedUsername = '';
    let lastCheckResult = null;
    let checkingUsername = false;

    function validateUsername() {
        const input = document.getElementById('username');
        const value = input.value.trim();
        const originalUsername = input.getAttribute('data-original-username') || '';
        
        // If username is the same as current, always valid
        if (value === originalUsername) {
            clearError('username');
            lastCheckedUsername = value;
            lastCheckResult = { valid: true, message: '' };
            updateSaveButtonState();
            return true;
        }

        // If checking the same value and we have a result, use cached result
        if (value === lastCheckedUsername && lastCheckResult !== null && !checkingUsername) {
            if (!lastCheckResult.valid) {
                showError('username', lastCheckResult.message);
                updateSaveButtonState();
            } else {
                clearError('username');
                updateSaveButtonState();
            }
            return lastCheckResult.valid;
        }

        // Check for spaces
        if (value.includes(' ')) {
            const result = { valid: false, message: 'Username should not contain spaces. Please choose another.' };
            showError('username', result.message);
            lastCheckedUsername = value;
            lastCheckResult = result;
            updateSaveButtonState();
            return false;
        }

        // Check minimum length
        if (value.length < 4) {
            const result = { valid: false, message: 'Username must be at least 4 characters long. Please choose another.' };
            showError('username', result.message);
            lastCheckedUsername = value;
            lastCheckResult = result;
            updateSaveButtonState();
            return false;
        }

        // Check maximum length
        if (value.length > 100) {
            const result = { valid: false, message: 'Username must not exceed 100 characters.' };
            showError('username', result.message);
            lastCheckedUsername = value;
            lastCheckResult = result;
            updateSaveButtonState();
            return false;
        }
  
        // Only check existence if different from original username
        if (value !== originalUsername) {
            if (!checkingUsername) {
                checkingUsername = true;
                // Show checking message without clearing previous error
                if (!lastCheckResult || lastCheckResult.valid) {
                    showError('username', 'Checking username availability...');
                }
                updateSaveButtonState();
            }

            clearTimeout(window.usernameTimeout);
            window.usernameTimeout = setTimeout(() => {
                fetch('/check-username/?username=' + encodeURIComponent(value))
                    .then(response => response.json())
                    .then(data => {
                        checkingUsername = false;
                        if (data.exists) {
                            lastCheckResult = { valid: false, message: 'This username is already taken. Please choose another.' };
                            showError('username', lastCheckResult.message);
                        } else {
                            lastCheckResult = { valid: true, message: '' };
                            clearError('username');
                        }
                        lastCheckedUsername = value;
                        updateSaveButtonState();
                    })
                    .catch(error => {
                        checkingUsername = false;
                        console.error('Error checking username:', error);
                        lastCheckResult = { valid: false, message: 'Error checking username. Please try again.' };
                        showError('username', lastCheckResult.message);
                        lastCheckedUsername = value;
                        updateSaveButtonState();
                    });
            }, 600);
            
            return false;
        }

        clearError('username');
        lastCheckedUsername = value;
        lastCheckResult = { valid: true, message: '' };
        updateSaveButtonState();
        return true;
    }
    
    document.getElementById('username').addEventListener('input', validateUsername);
    

    // List of fields to validate
    const fields = [
        {id: 'first-name', label: 'First name'},
        // Middle name is optional, skip validation
        {id: 'last-name', label: 'Last name'},
        {id: 'house-no', label: 'House number'},
        {id: 'street-village', label: 'Street or village'},
        {id: 'barangay', label: 'Barangay'},
        {id: 'city', label: 'City'},
        {id: 'province', label: 'Province'},
        {id: 'state', label: 'State'},
        {id: 'zipcode', label: 'Zipcode'},
        {id: 'contact-number', label: 'Contact number'},
        {id: 'email', label: 'Email'},
        {id: 'birthdate', label: 'Birthdate'},
        {id: 'gender', label: 'Gender'}
        // Username is readonly/disabled, skip validation
    ];
    fields.forEach(field => {
        const input = document.getElementById(field.id);
        if (input) {
            input.addEventListener('input', function() {
                validateNotEmpty(field.id, field.label);
            });
            // Initial check
            validateNotEmpty(field.id, field.label);
        }
    });
    // Attach special validation
    document.getElementById('zipcode').addEventListener('input', validateZipcode);
    document.getElementById('contact-number').addEventListener('input', validateContactNumber);
    document.getElementById('email').addEventListener('input', validateEmail);
    document.getElementById('state').addEventListener('input', validateState);
    document.getElementById('birthdate').addEventListener('input', validateBirthdate);
    document.getElementById('gender').addEventListener('change', validateGender);
    // Initial check for special fields
    validateZipcode();
    validateContactNumber();
    validateEmail();
    validateState();
    validateBirthdate();
    validateGender();
    validateUsername();
    
    // Initial update of save button state
    updateSaveButtonState();
}
