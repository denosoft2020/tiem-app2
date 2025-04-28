document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("signInForm").addEventListener("submit", async function(event) {
        event.preventDefault();
        
        const username = document.getElementById("username").value.trim();
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value.trim();
        const confirmPassword = document.getElementById("confirmPassword").value.trim();
        const acceptLicense = document.getElementById("acceptLicense").checked;
        
        // Validate email format
        const emailPattern = /^[^ ]+@[^ ]+\.[a-z]{2,3}$/;
        if (!email.match(emailPattern)) {
            alert("Please enter a valid email address.");
            return;
        }

        if (password !== confirmPassword) {
            alert("Passwords do not match.");
            return;
        }
        
        if (!acceptLicense) {
            alert("You must accept the license to proceed.");
            return;
        }

        // Hash the password before sending
        const hashedPassword = await sha256(password);

        alert(`Sign-up successful! Username: ${username}, Email: ${email}, Hashed Password: ${hashedPassword}`);

        // Redirect to login page
        window.location.href = "log-in.html";
    });

    // SHA-256 Hash Function
    async function sha256(str) {
        const buffer = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
        return Array.from(new Uint8Array(buffer)).map(b => b.toString(16).padStart(2, '0')).join('');
    }
});
