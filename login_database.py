import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------- Config ----------------
SERVICE_JSON = "campusvibe-2025-firebase-adminsdk-fbsvc-661818db3a.json"

# ---------------- Firebase Init ----------------
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(SERVICE_JSON)
        firebase_admin.initialize_app(cred)
    except FileNotFoundError:
        st.error(f"Error: The service JSON file '{SERVICE_JSON}' was not found.")
        st.stop()
    except Exception as e:
        st.error(f"Firebase initialization error: {e}")
        st.stop()

db = firestore.client()

# ---------------- Firestore Helpers ----------------
def register_user(name, email, password):
    if not name or not email or not password:
        return False, "All fields required"
    doc = db.collection("users").document(email).get()
    if doc.exists:
        return False, "User already exists"
    db.collection("users").document(email).set({
        "name": name,
        "email": email,
        "password": password
    })
    return True, "Account created successfully!"

def login_user(email, password):
    doc = db.collection("users").document(email).get()
    if not doc.exists:
        return False, "User not found."
    data = doc.to_dict()
    if data["password"] == password:
        return True, data["name"]
    return False, "Invalid password."

# ---------------- Session Defaults ----------------
if "auth" not in st.session_state:
    st.session_state.auth = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "show_signup" not in st.session_state:
    st.session_state.show_signup = False

st.set_page_config(page_title="CampusVibe", layout="centered")

# ---------------- Page Header ----------------
st.markdown(
    "<h1 style='text-align:center;color:#2575fc;font-family:Segoe UI;'>CampusVibe</h1>",
    unsafe_allow_html=True,
)

# ---------------- Login/Register Container ----------------
with st.container():
    col1, col2 = st.columns([1,1])

    if not st.session_state.show_signup:
        # ---- Login Form ----
        with col1:
            st.subheader("Sign In")
            login_email = st.text_input("Email", key="login_email")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            if st.button("SIGN IN"):
                ok, msg = login_user(login_email, login_pass)
                if ok:
                    st.session_state.auth = True
                    st.session_state.user_email = login_email
                    st.session_state.user_name = msg
                    st.success(f"Welcome {msg}!")
                    st.experimental_rerun()
                else:
                    st.error(msg)
            st.markdown(
                "<div style='text-align:center;margin-top:10px;'>Don't have an account? <a href='#' style='color:#6a11cb;' onclick=''>Sign Up</a></div>",
                unsafe_allow_html=True,
            )
            if st.button("Go to Sign Up"):
                st.session_state.show_signup = True

        # Empty second column to simulate slide effect
        with col2:
            st.write("")

    else:
        # ---- Register Form ----
        with col2:
            st.subheader("Create Account")
            signup_name = st.text_input("Name", key="signup_name")
            signup_email = st.text_input("Email", key="signup_email")
            signup_pass = st.text_input("Password", type="password", key="signup_pass")
            if st.button("SIGN UP"):
                ok, msg = register_user(signup_name, signup_email, signup_pass)
                if ok:
                    st.success(msg)
                    st.session_state.show_signup = False
                else:
                    st.error(msg)
            if st.button("Back to Sign In"):
                st.session_state.show_signup = False

        # Empty first column to simulate slide effect
        with col1:
            st.write("")

# ---------------- Dashboard ----------------
if st.session_state.auth:
    st.markdown("---")
    st.success(f"🚀 Logged in as: {st.session_state.user_email}")
    st.write(f"Hello **{st.session_state.user_name}**, welcome to the CampusVibe dashboard.")
    if st.button("Logout"):
        st.session_state.auth = False
        st.session_state.user_email = None
        st.session_state.user_name = None
        st.experimental_rerun()
