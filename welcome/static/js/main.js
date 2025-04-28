// Trigger camera on mobile devices
function openCameraForProfilePicture() {
    const fileInput = document.getElementById('id_profile_picture');
    fileInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const form = this.closest('form');
            form.submit();
        }
    });
    fileInput.click();
}

// For post creation
document.addEventListener('DOMContentLoaded', function() {
    // Camera buttons
    document.querySelectorAll('.camera-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const fileInput = this.closest('form').querySelector('input[type="file"]');
            fileInput.setAttribute('capture', 'environment');
            fileInput.click();
        });
    });
    
    // Gallery buttons
    document.querySelectorAll('.gallery-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const fileInput = this.closest('form').querySelector('input[type="file"]');
            fileInput.removeAttribute('capture');
            fileInput.click();
        });
    });
});