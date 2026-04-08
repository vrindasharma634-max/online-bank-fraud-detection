function toggleForm() {
    const login = document.getElementById("loginForm");
    const signup = document.getElementById("signupForm");
    const title = document.getElementById("title");
    const toggleText = document.getElementById("toggleText");

    login.classList.toggle("hidden");
    signup.classList.toggle("hidden");

    if (login.classList.contains("hidden")) {
        title.innerText = "Sign Up";
        toggleText.innerHTML = `Already have an account? 
        <span onclick="toggleForm()">Login</span>`;
    } else {
        title.innerText = "Login";
        toggleText.innerHTML = `Don't have an account? 
        <span onclick="toggleForm()">Sign Up</span>`;
    }
}