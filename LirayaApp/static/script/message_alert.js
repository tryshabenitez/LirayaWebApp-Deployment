document.addEventListener('DOMContentLoaded', () => {
  // For login page error banner
  const alert = document.querySelector('.error-alert');
  if (alert) {
    setTimeout(() => {
      alert.style.display = 'none';
    }, 5000);
  }

  // For field-level errors (e.g., in force change password)
  const fieldErrors = document.querySelectorAll('.field-error');
  fieldErrors.forEach((error) => {
    setTimeout(() => {
      error.style.transition = 'opacity 0.5s ease';
      error.style.opacity = '0';
      setTimeout(() => {
        error.remove();
      }, 500); // after fade out
    }, 5000);
  });
});
