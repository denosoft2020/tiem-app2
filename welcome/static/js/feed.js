document.addEventListener('DOMContentLoaded', function() {
    // Auto-play videos when they come into view
    const videoContainers = document.querySelectorAll('.video-container');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            const video = entry.target.querySelector('video');
            if (video) {
                if (entry.isIntersecting) {
                    video.play().catch(e => console.log("Auto-play prevented:", e));
                } else {
                    video.pause();
                }
            }
        });
    }, { threshold: 0.7 });

    videoContainers.forEach(container => {
        observer.observe(container);
    });

    // Like functionality
    document.querySelectorAll('.like-button').forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.postId;
            const isLiked = this.querySelector('i').classList.contains('fas');
            const likeCount = this.querySelector('.action-count');
            
            // Immediate UI feedback
            const icon = this.querySelector('i');
            icon.classList.toggle('far');
            icon.classList.toggle('fas');
            
            // Update count temporarily
            const currentCount = parseInt(likeCount.textContent);
            likeCount.textContent = isLiked ? currentCount - 1 : currentCount + 1;
            
            // Send request to server
            fetch(`/like/${postId}/`, {
                method: isLiked ? 'DELETE' : 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    // Revert if failed
                    icon.classList.toggle('far');
                    icon.classList.toggle('fas');
                    likeCount.textContent = currentCount;
                }
            });
        });
    });

    // Follow functionality
    document.querySelectorAll('.follow-btn').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.dataset.userId;
            const isFollowing = this.classList.contains('following');
            const followIndicator = this.closest('.video-container').querySelector('.follow-indicator i');
            
            // Immediate UI feedback
            this.classList.toggle('following');
            
            if (this.classList.contains('following')) {
                this.textContent = 'Following';
                if (followIndicator) {
                    followIndicator.classList.remove('fa-plus-circle', 'not-followed');
                    followIndicator.classList.add('fa-check-circle', 'followed');
                }
            } else {
                this.textContent = 'Follow';
                if (followIndicator) {
                    followIndicator.classList.remove('fa-check-circle', 'followed');
                    followIndicator.classList.add('fa-plus-circle', 'not-followed');
                }
            }
            
            // Send request to server
            fetch(`/follow/${userId}/`, {
                method: isFollowing ? 'DELETE' : 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    // Revert if failed
                    this.classList.toggle('following');
                    if (this.classList.contains('following')) {
                        this.textContent = 'Following';
                        if (followIndicator) {
                            followIndicator.classList.remove('fa-plus-circle', 'not-followed');
                            followIndicator.classList.add('fa-check-circle', 'followed');
                        }
                    } else {
                        this.textContent = 'Follow';
                        if (followIndicator) {
                            followIndicator.classList.remove('fa-check-circle', 'followed');
                            followIndicator.classList.add('fa-plus-circle', 'not-followed');
                        }
                    }
                }
            });
        });
    });

    // Share functionality
    document.querySelectorAll('.share-button').forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.closest('.video-container').dataset.postId;
            // Implement share functionality
            if (navigator.share) {
                navigator.share({
                    title: 'Check out this video',
                    url: `/post/${postId}/`
                }).catch(e => console.log('Share cancelled:', e));
            } else {
                // Fallback for browsers that don't support Web Share API
                prompt('Copy this link to share:', `${window.location.origin}/post/${postId}/`);
            }
        });
    });

    // View count increment when video is played
    document.querySelectorAll('video').forEach(video => {
        video.addEventListener('play', function() {
            const postId = this.closest('.video-container').dataset.postId;
            // Send view count to server
            fetch(`/view/${postId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN
                }
            });
        });
    });
});