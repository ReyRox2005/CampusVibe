import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Custom Auth Page", layout="centered")

components.html("""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    body {
      margin: 0;
      font-family: 'Segoe UI', sans-serif;
      background: #d9e2ef;
      height: 100vh;
      width: 100vw;
      display: flex;
      justify-content: center;
      align-items: center;
    }
    .container {
      width: 98vw;
      height: 85vh;
      background: #fff;
      border-radius: 0;   /* 👈 outer box se bhi curve hata diya */
      display: flex;
      overflow: hidden;
      box-shadow: 0px 8px 25px rgba(0,0,0,0.25);
      transition: all 0.6s ease-in-out;
      position: relative;
    }
    .form-container {
      position: absolute;
      top: 0;
      height: 100%;
      transition: all 0.6s ease-in-out;
    }
    .sign-in-container {
      left: 0;
      width: 50%;
      z-index: 2;
    }
    .sign-up-container {
      left: 0;
      width: 50%;
      opacity: 0;
      z-index: 1;
    }
    .container.right-panel-active .sign-up-container {
      transform: translateX(100%);
      opacity: 1;
      z-index: 5;
    }
    .container.right-panel-active .sign-in-container {
      transform: translateX(100%);
      opacity: 0;
    }
    .overlay-container {
      position: absolute;
      top: 0;
      left: 50%;
      width: 50%;
      height: 100%;
      background: linear-gradient(135deg, #6a11cb, #2575fc);
      color: white;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      padding: 40px;
      text-align: center;
      box-sizing: border-box;
      transition: all 0.6s ease-in-out;
      /* 👇 curve lines hata di */
      border-top-left-radius: 0;
      border-bottom-left-radius: 0;
    }
    .container.right-panel-active .overlay-container {
      transform: translateX(-100%);
    }
    h2 { margin: 0 0 15px; }
    input {
      width: 100%;
      padding: 12px;
      margin: 10px 0;
      border-radius: 8px;
      border: 1px solid #ccc;
      font-size: 14px;
    }
    button {
      width: 100%;
      padding: 12px;
      margin-top: 10px;
      border: none;
      border-radius: 8px;
      font-size: 16px;
      font-weight: bold;
      cursor: pointer;
    }
    .signin { background: #6a11cb; color: #fff; }
    .signin:hover { background: #2575fc; }
    .signup { background: #6a11cb; color: #fff; }
    .overlay-container p {
      max-width: 280px;
      font-size: 15px;
      line-height: 1.4em;
      margin-bottom: 20px;
    }
  </style>
</head>
<body>
  <div class="container" id="mainContainer">
    <!-- Sign In -->
    <div class="form-container sign-in-container">
      <div style="padding:50px 40px;">
        <h2>Sign In</h2>
        <p>or use your email password</p>
        <input type="text" placeholder="Email">
        <input type="password" placeholder="Password">
        <p style="font-size: 12px; color: gray;">Forgot your password?</p>
        <button class="signin">SIGN IN</button>
      </div>
    </div>

    <!-- Sign Up -->
    <div class="form-container sign-up-container">
      <div style="padding:50px 40px;">
        <h2>Create Account</h2>
        <p>Use your email for registration</p>
        <input type="text" placeholder="Name">
        <input type="text" placeholder="Email">
        <input type="password" placeholder="Password">
        <button class="signup">SIGN UP</button>
      </div>
    </div>

    <!-- Overlay -->
    <div class="overlay-container">
      <h2>Hello, Friend!</h2>
      <p>Register with your personal details to use all of site features</p>
      <button onclick="togglePanel()">SIGN UP</button>
    </div>
  </div>

  <script>
    function togglePanel() {
      document.getElementById('mainContainer').classList.toggle("right-panel-active");
    }
  </script>
</body>
</html>
""", height=750)
