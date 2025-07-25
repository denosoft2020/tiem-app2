document.addEventListener("DOMContentLoaded", function() {
    const friendsContainer = document.querySelector(".suggested-friends");
    const postsContainer = document.querySelector(".friends-posts");
    
    setTimeout(() => {
        friendsContainer.innerHTML = "";
        const friends = [
            "👤 John Doe - Add Friend",
            "👤 Jane Smith - Add Friend",
            "👤 Alex Johnson - Add Friend"
        ];
        
        friends.forEach(friend => {
            const p = document.createElement("p");
            p.textContent = friend;
            friendsContainer.appendChild(p);
        });
    }, 2000);
    
    setTimeout(() => {
        postsContainer.innerHTML = "";
        const posts = [
            "📸 John posted a new photo!",
            "🎥 Jane uploaded a video!",
            "💬 Alex shared a new status update!"
        ];
        
        posts.forEach(post => {
            const p = document.createElement("p");
            p.textContent = post;
            postsContainer.appendChild(p);
        });
    }, 3000);
});