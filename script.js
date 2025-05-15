// Your Firebase config object (replace with your own from Firebase Console)
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
  // Add two new changes 
  measurementId: "Your measurement ID"
  databaseURL: "Add Your database URL"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const database = firebase.database();

const registerForm = document.getElementById("register-form");
const message = document.getElementById("message");

registerForm.addEventListener("submit", function (e) {
  e.preventDefault();
  const email = registerForm["email"].value;
  const password = registerForm["password"].value;
  const username = registerForm["username"].value;

  auth.createUserWithEmailAndPassword(email, password)
    .then(userCredential => {
      const user = userCredential.user;
      return database.ref("users/" + user.uid).set({
        username: username,
        email: email,
        createdAt: new Date().toISOString()
      });
    })
    .then(() => {
      message.textContent = "Account created and data saved!";
      message.style.color = "lightgreen";
    })
    .catch(error => {
      message.textContent = "Error: " + error.message;
      message.style.color = "red";
    });
});

