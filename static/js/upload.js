document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('upload-form');
    const previewContainer = document.getElementById('preview-container');
    const emptyState = previewContainer.querySelector('.empty-state');
    const cameraInput = document.getElementById('camera-input');
    const galleryInput = document.getElementById('gallery-input');
    
    // Create loading overlay
    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay';
    loadingOverlay.innerHTML = '<div class="spinner"></div>';
    previewContainer.appendChild(loadingOverlay);
    
    // Handle file selection from either input
    function handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        // Clear previous preview
        previewContainer.innerHTML = '';
        previewContainer.appendChild(loadingOverlay);
        loadingOverlay.style.display = 'flex';
        
        // Create appropriate media element
        let mediaElement;
        if (file.type.startsWith('image/')) {
            mediaElement = document.createElement('img');
        } else if (file.type.startsWith('video/')) {
            mediaElement = document.createElement('video');
            mediaElement.controls = true;
            
            // Add custom controls
            const controls = document.createElement('div');
            controls.className = 'media-controls';
            controls.innerHTML = `
                <button onclick="this.parentNode.parentNode.querySelector('video').play()">
                    <i class="fas fa-play"></i>
                </button>
                <button onclick="this.parentNode.parentNode.querySelector('video').pause()">
                    <i class="fas fa-pause"></i>
                </button>
            `;
            previewContainer.appendChild(controls);
        }
        
        mediaElement.className = 'preview-media';
        mediaElement.onloadeddata = mediaElement.onload = function() {
            loadingOverlay.style.display = 'none';
        };
        
        mediaElement.src = URL.createObjectURL(file);
        previewContainer.insertBefore(mediaElement, loadingOverlay);
    }
    
    // Event listeners for both file inputs
    cameraInput.addEventListener('change', handleFileSelect);
    galleryInput.addEventListener('change', handleFileSelect);
    
    // Form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate media was selected
        if (!cameraInput.files.length && !galleryInput.files.length) {
            alert('Please select a photo or video first');
            return;
        }
        
        loadingOverlay.style.display = 'flex';
        
        const formData = new FormData(form);
        
        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = data.redirect_url || '/feed/';
            } else {
                alert(data.message || 'Error uploading post');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while uploading');
        })
        .finally(() => {
            loadingOverlay.style.display = 'none';
        });
    });
});