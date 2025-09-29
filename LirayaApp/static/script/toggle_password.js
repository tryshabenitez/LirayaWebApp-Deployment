function togglePassword(passwordFieldId) {
    var passwordField = document.getElementById(passwordFieldId);
    var eyeIcon = document.getElementById('eye-icon-' + passwordFieldId);

    if (passwordField.type === "password") {
        passwordField.type = "text";
        eyeIcon.src = "/static/images/open_eye_white.png";
    } else {
        passwordField.type = "password";
        eyeIcon.src = "/static/images/hidden_eye_white.png";
    }
}
