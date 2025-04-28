document.addEventListener("DOMContentLoaded", function() {
    const notificationFeed = document.querySelector(".notification-feed");
    
    // Simulate loading notifications from backend
    setTimeout(() => {
        notificationFeed.innerHTML = "";
        const notifications = [
            "🔔 You have a new follower!",
            "💬 Someone commented on your post!",
            "❤️ Your post got 10 likes!"
        ];
        
        notifications.forEach(notification => {
            const p = document.createElement("p");
            p.textContent = notification;
            notificationFeed.appendChild(p);
        });
    }, 2000);
});