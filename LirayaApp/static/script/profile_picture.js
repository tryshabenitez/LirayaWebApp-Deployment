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
            
            // Handle cancel action
            document.getElementById('crop-cancel').addEventListener('click', function() {
                // Reset the file input so the same file can be selected again if needed
                document.getElementById('profile-picture-upload').value = '';
                
                // Close the modal
                document.getElementById('cropper-modal').style.display = 'none';
                
                // Destroy cropper to release resources
                cropper.destroy();
            });
        };
        reader.readAsDataURL(file);
    }
});

/// deactivate account /////
document.getElementById("deactivate-button").addEventListener("click", function() {
    document.getElementById("deactivateModal").style.display = "flex";

    let countdown = 5;
    const countdownElement = document.getElementById("countdown");
    const spinner = document.getElementById("countdown-spinner");
    const deactivateButton = document.getElementById("deactivate-confirm");
    deactivateButton.style.display = "none";
    deactivateButton.disabled = true;

    countdownElement.textContent = countdown;
    countdownElement.style.display = "block";
    spinner.style.display = "inline-block";

    let timer = setInterval(function() {
        countdown--;
        countdownElement.textContent = countdown > 0 ? countdown : 0;
        if (countdown <= 0) {
            clearInterval(timer);
            deactivateButton.disabled = false;
            deactivateButton.style.display = "inline-block";
            countdownElement.style.display = "none";
            spinner.style.display = "none";
        }
    }, 1000);

    document.getElementById("cancel-deactivate").onclick = function() {
        document.getElementById("deactivateModal").style.display = "none";
        clearInterval(timer);
    };

    deactivateButton.onclick = function() {
        window.location.href = "/deactivate_account/";
    };
});

