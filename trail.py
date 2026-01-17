
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------- Config ----------------
SERVICE_JSON = "campusvibe-2025-firebase-adminsdk-fbsvc-a228980641.json"

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

st.set_page_config(page_title="CampusVibe", layout="wide")

# =========================================================
# ---------------- LOGIN / REGISTER -----------------------
# =========================================================
if not st.session_state.auth:

    st.markdown(
        "<h1 style='text-align:center;color:#2575fc;font-family:Segoe UI;'>CampusVibe</h1>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])

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
                    st.rerun()   # ✅ fixed
                else:
                    st.error(msg)
            if st.button("Go to Sign Up"):
                st.session_state.show_signup = True

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

        with col1:
            st.write("")

# =========================================================
# ---------------- HOME / DASHBOARD -----------------------
# =========================================================
else:
    # Custom CSS
    st.markdown("""
        <style>
            .block-container {
                padding: 1rem 2rem;
            }
            .note-card {
                background-color: #f4f0ff;
                padding: 1rem;
                border-radius: 10px;
                margin-bottom: 1rem;
                box-shadow: 0 0 5px #ccc;
            }
            .note-title {
                font-weight: 600;
            }
            .chat-box {
                background-color: #f0f4ff;
                padding: 1rem;
                border-radius: 10px;
            }
            .ask-box {
                background-color: #fdf4ff;
                padding: 1rem;
                border-radius: 10px;
            }
            .submit-button {
                background-color: #6557f5;
                color: white;
                padding: 0.4rem 1.2rem;
                border-radius: 5px;
                margin: 0.5rem 0;
                border: none;
            }
            .accept-button {
                background-color: #30c05b;
                color: white;
                border-radius: 5px;
                padding: 0.3rem 0.8rem;
                border: none;
            }
            .reject-button {
                background-color: #e74c3c;
                color: white;
                border-radius: 5px;
                padding: 0.3rem 0.8rem;
                border: none;
            }
        </style>
    """, unsafe_allow_html=True)

    # ---------------- HEADER ----------------
    col_logo, col_search, col_notify = st.columns([2, 6, 1])
    col_logo.markdown("### 🎓 CampusVibe")
    col_search.text_input("Search anything...", label_visibility="collapsed", placeholder="Search...")
    col_notify.markdown("🔔", unsafe_allow_html=True)

    st.markdown("---")

    # ---------------- SIDEBAR ----------------
    with st.sidebar:
        st.markdown(f"👋 Welcome, **{st.session_state.user_name}**")
        if st.button("Logout"):
            st.session_state.auth = False
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.rerun()   # ✅ fixed

        st.markdown("### 🎯 Filters")
        st.selectbox("Select Year", ["1st Year", "2nd Year", "3rd Year", "4th Year"])
        st.selectbox("Branch", ["CSE", "ECE", "ME", "CE"])
        st.selectbox("Subject", ["DSA", "OS", "DBMS", "CN", "AI"])

        st.markdown("<button class='submit-button'>Upload Notes 🧑‍🏫</button>", unsafe_allow_html=True)
        st.markdown("<button class='submit-button' style='background-color:#28a745;'>Chat with Senior💬</button>", unsafe_allow_html=True)

    # ---------------- MAIN AREA ----------------
    st.markdown("## 🔥 Trending Notes")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class='note-card'>
            <div class='note-title'>📄 DSA Unit 1</div>
            ⭐ 32 downloads<br><br>
            <button class='submit-button'>View</button>
            <button class='submit-button'>Download</button>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class='note-card'>
            <div class='note-title'>📄 OS Unit 2</div>
            ⭐ 42 downloads<br><br>
            <button class='submit-button'>View</button>
            <button class='submit-button'>Download</button>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class='note-card'>
            <div class='note-title'>📄 DBMS Unit 3</div>
            ⭐ 52 downloads<br><br>
            <button class='submit-button'>View</button>
            <button class='submit-button'>Download</button>
        </div>""", unsafe_allow_html=True)

    # ---------------- Chat Requests ----------------
    st.markdown("""
    <div class='chat-box'>
        <h4>💬 Chat Requests</h4>
        <p><i>"anonFirstYr23" wants to connect. Topic: DSA</i></p>
        <button class='accept-button'>Accept</button>
        <button class='reject-button'>Reject</button>
    </div>
    """, unsafe_allow_html=True)

    # ---------------- Ask a Senior ----------------
    st.markdown("""
    <div class='ask-box'>
        <h4>🧠 Ask a Senior</h4>
        <p><i>"What to study for placement in 2nd year?"</i></p>
        <button class='submit-button'>Answer Question</button>
    </div>
    """, unsafe_allow_html=True)

    # ---------------- Ask your own ----------------
    st.markdown("### Ask Your Question")
    user_q = st.text_area("Type your question here...")
