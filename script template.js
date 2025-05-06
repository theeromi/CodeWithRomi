// Your Firebase config object (replace with your own from Firebase Console)
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

const auth = firebase.auth();
const loginForm = document.getElementById("login-form");
const message = document.getElementById("message");

loginForm.addEventListener("submit", function (e) {
  e.preventDefault();
  const email = loginForm["email"].value;
  const password = loginForm["password"].value;

  auth.signInWithEmailAndPassword(email, password)
    .then(userCredential => {
      message.textContent = "Login successful!";
      message.style.color = "lightgreen";
    })
    .catch(error => {
      message.textContent = "Error: " + error.message;
      message.style.color = "red";
    });
});
