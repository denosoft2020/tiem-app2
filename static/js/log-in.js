document.getElementById("login-form").addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent default form submission

    let email = document.getElementById("email").value;
    let password = document.getElementById("password").value;
    
    // Get CSRF token from the form's hidden input
    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    fetch("/login/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken() // Add CSRF token in the headers
        },
        body: JSON.stringify({ email: email, password: password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.redirect) {
            window.location.href = data.redirect; // Redirect on success
        } else {
            alert(data.message); // Show error message
        }
    })
    .catch(error => console.error("Login Error:", error));
});
