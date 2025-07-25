document.addEventListener("DOMContentLoaded", () => {
    const googleLogin = document.getElementById("googleLogin");
    const facebookLogin = document.getElementById("facebookLogin");
    const createAccount = document.getElementById("createAccount");

    googleLogin.addEventListener("click", () => {
        window.location.href = "/auth/google/"; // Django OAuth URL
    });

    facebookLogin.addEventListener("click", () => {
        window.location.href = "/auth/facebook/"; // Django OAuth URL
    });

    createAccount.addEventListener("click", () => {
        window.location.href = "sign-in.html";
    });
});
