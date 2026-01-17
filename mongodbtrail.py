import streamlit as st
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime

# --- Initialization Function ---

@st.cache_resource
def init_mongo_connection():
    """Initializes and caches the MongoDB connection and database object."""
    try:
        # 1. Secret Check
        if "mongo" not in st.secrets or "uri" not in st.secrets["mongo"] or "database_name" not in st.secrets["mongo"]:
            st.error("MongoDB secrets not fully configured. Check `secrets.toml` for [mongo] uri and database_name.")
            st.stop()
            
        uri = st.secrets["mongo"]["uri"]
        DB_NAME = st.secrets["mongo"]["database_name"]

        # 2. Connection
        client = MongoClient(uri)
        
        # 3. Verification
        client.admin.command('ping') 
        
        # 4. Database Selection
        database = client[DB_NAME]
        
        st.success("MongoDB connected successfully.") 
        
        # Return both the client and the database object
        return client, database 
        
    except Exception as e:
        st.error(f"MongoDB connection error: Check URI, password, or network rules. Error: {e}")
        st.stop()

# Initialize MongoDB client and database
client, db = init_mongo_connection() 

# ---------------- MongoDB Helpers ----------------

def get_user_collection():
    return db["users"] 

def get_notes_collection():
    return db["notes"] 

def register_user(name, email, password):
    if not name or not email or not password:
        return False, "All fields required"
    users_coll = get_user_collection()
    if users_coll.find_one({"_id": email}): 
        return False, "User already exists. Please sign in."
    
    users_coll.insert_one({
        "_id": email, 
        "name": name,
        "email": email,
        "password": password 
    })
    return True, "Account created successfully! You can now sign in."

def login_user(email, password):
    users_coll = get_user_collection()
    user_doc = users_coll.find_one({"_id": email})
    if not user_doc:
        return False, "User not found. Please register."
    if user_doc.get("password") == password:
        return True, user_doc.get("name", email)
    return False, "Invalid password."

@st.cache_data(ttl=600) 
def get_trending_notes():
    notes_coll = get_notes_collection()
    try:
        notes = list(notes_coll.find().sort("downloads", pymongo.DESCENDING).limit(3))
        for note in notes:
            if isinstance(note["_id"], ObjectId):
                 note["_id"] = str(note["_id"])
        return notes
    except Exception as e:
        st.error(f"Error fetching notes from MongoDB: {e}")
        return []

def log_download(note_id):
    notes_coll = get_notes_collection()
    try:
        object_id = ObjectId(note_id) 
        notes_coll.update_one(
            {"_id": object_id},
            {"$inc": {"downloads": 1}}
        )
    except:
        notes_coll.update_one(
            {"_id": note_id},
            {"$inc": {"downloads": 1}}
        )
    get_trending_notes.clear()

# --- NEW FEEDBACK HELPER FUNCTION ---
def submit_note_feedback(note_id, user_email, feedback_text):
    notes_coll = get_notes_collection()
    
    new_feedback = {
        "user_email": user_email,
        "text": feedback_text,
        "submitted_at": datetime.datetime.now()
    }
    
    try:
        object_id = ObjectId(note_id) 
        notes_coll.update_one(
            {"_id": object_id},
            {"$push": {"feedback": new_feedback}}
        )
        return True
    except Exception as e:
        notes_coll.update_one(
            {"_id": note_id},
            {"$push": {"feedback": new_feedback}}
        )
        return True
# --- END NEW HELPER ---

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
# ---------------- LOGIN / REGISTER (MongoDB Auth) -----------------------
# =========================================================
if not st.session_state.auth:

    st.markdown(
        "<h1 style='text-align:center;color:#2575fc;font-family:Segoe UI;'>CampusVibe</h1>",
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown("<br><br>", unsafe_allow_html=True) 
        col1, col2, col3 = st.columns([1, 2, 1]) 

        if not st.session_state.show_signup:
            # ---- Login Form ----
            with col2:
                with st.form("login_form"):
                    st.subheader("Sign In")
                    login_email = st.text_input("Email", key="login_email_input")
                    login_pass = st.text_input("Password", type="password", key="login_pass_input")
                    submitted = st.form_submit_button("SIGN IN", type="primary", use_container_width=True)

                    if submitted:
                        ok, msg = login_user(login_email, login_pass)
                        if ok:
                            st.session_state.auth = True
                            st.session_state.user_email = login_email
                            st.session_state.user_name = msg
                            st.rerun() 
                        else:
                            st.error(msg)
                    
                if st.button("Go to Sign Up", use_container_width=True):
                    st.session_state.show_signup = True
                    st.rerun()

        else:
            # ---- Register Form ----
            with col2:
                with st.form("signup_form"):
                    st.subheader("Create Account")
                    signup_name = st.text_input("Name", key="signup_name_input")
                    signup_email = st.text_input("Email", key="signup_email_input")
                    signup_pass = st.text_input("Password", type="password", key="signup_pass_input")
                    submitted = st.form_submit_button("SIGN UP", type="primary", use_container_width=True)
                    
                    if submitted:
                        ok, msg = register_user(signup_name, signup_email, signup_pass)
                        if ok:
                            st.success(msg)
                            st.session_state.show_signup = False
                            st.rerun() 
                        else:
                            st.error(msg)
                            
                if st.button("Back to Sign In", use_container_width=True):
                    st.session_state.show_signup = False
                    st.rerun()

# =========================================================
# ---------------- HOME / DASHBOARD -----------------------
# =========================================================
else:
    # Custom CSS
    st.markdown("""
        <style>
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
            .chat-box, .ask-box {
                padding: 1rem;
                border-radius: 10px;
                margin-top: 20px;
            }
            .chat-box { background-color: #f0f4ff; }
            .ask-box { background-color: #fdf4ff; }
            .submit-button, .accept-button, .reject-button {
                padding: 0.4rem 1.2rem;
                border-radius: 5px;
                margin-right: 10px;
                border: none;
                color: white;
                cursor: pointer;
            }
            .submit-button { background-color: #6557f5; }
            .accept-button { background-color: #30c05b; }
            .reject-button { background-color: #e74c3c; }
        </style>
    """, unsafe_allow_html=True)

    # ---------------- HEADER ----------------
    col_logo, col_search, col_notify = st.columns([2, 6, 1])
    col_logo.markdown("### 🎓 CampusVibe")
    col_search.text_input("Search anything...", label_visibility="collapsed", placeholder="Search for notes, seniors, or questions...")
    col_notify.markdown("🔔", unsafe_allow_html=True)

    st.markdown("---")

    # ---------------- SIDEBAR ----------------
    with st.sidebar:
        st.markdown(f"👋 Welcome, **{st.session_state.user_name}**")
        if st.button("Logout", use_container_width=True):
            st.session_state.auth = False
            st.session_state.user_email = None
            st.session_state.user_name = None
            st.rerun()

        st.markdown("### 🎯 Filters")
        selected_year = st.selectbox("Select Year", ["1st Year", "2nd Year", "3rd Year", "4th Year"], key="filter_year")
        selected_branch = st.selectbox("Branch", ["CSE", "ECE", "ME", "CE"], key="filter_branch")
        selected_subject = st.selectbox("Subject", ["DSA", "OS", "DBMS", "CN", "AI"], key="filter_subject")
        
        st.markdown("<button class='submit-button' style='background-color:#28a745;'>Chat with Senior💬</button>", unsafe_allow_html=True)

    # ---------------- MAIN AREA - Trending Notes ----------------
    
    trending_notes = get_trending_notes()
    st.markdown("## 🔥 Trending Notes")

    cols = st.columns(3)

    if not trending_notes:
        st.info("No notes available yet. Please ask an administrator to upload note metadata via MongoDB Compass.")

    for i, note in enumerate(trending_notes):
        note_id = note["_id"]
        download_url = note.get("download_url", "#") 
        
        with cols[i % 3]: 
            
            # --- NOTE CARD DISPLAY ---
            st.markdown(f"""
            <div class='note-card'>
                <div class='note-title'>📄 {note.get('name', 'N/A')}</div>
                <span>Subject: **{note.get('subject', 'N/A')}**</span><br>
                <span>Branch: **{note.get('branch', 'N/A')}**</span><br>
                <span>Year: **{note.get('year', 'N/A')}**</span><br>
                ⭐ {note.get('downloads', 0)} downloads<br><br>
            </div>""", unsafe_allow_html=True)
            
            # --- ACTION BUTTONS ---

            # 1. VIEW/DOWNLOAD Link (Reliable navigation - No 'key' needed)
            st.link_button(
                "⬇️ View/Download Notes (Click Here)", 
                url=download_url, 
                use_container_width=True,
                help="Opens the file in a new tab."
            )
            
            # 2. LOG COUNT: Separate button to track the download count
            # Use a callback function to handle the logging and rerunning
            def log_and_rerun_download(n_id):
                log_download(n_id)
                st.toast(f"Download count updated for {note.get('name')}!", icon='👍')
                st.rerun() 
            
            st.button(
                "Log Download Count", 
                key=f"log_{note_id}", 
                use_container_width=True, 
                type="secondary",
                on_click=log_and_rerun_download,
                args=(note_id,)
            )

            # --- DEDICATED FEEDBACK FORM ---
            with st.form(key=f"feedback_form_{note_id}", clear_on_submit=True):
                feedback_text = st.text_input(
                    "Quick Feedback (e.g., outdated, wanted new one)", 
                    key=f"fb_input_{note_id}",
                    max_chars=100,
                    label_visibility="visible"
                )
                feedback_submitted = st.form_submit_button("Submit Feedback", type="secondary")

                if feedback_submitted:
                    if len(feedback_text.split()) < 2:
                        st.warning("Please provide a little more detail for feedback.")
                    else:
                        submit_note_feedback(note_id, st.session_state.user_email, feedback_text)
                        st.success("Feedback submitted! Admins will see it in MongoDB.")

    # ---------------- Other Sections ----------------
    st.markdown("---")

    col_chat, col_ask = st.columns(2)
    
    with col_chat:
        st.markdown("""
        <div class='chat-box'>
            <h4>💬 Chat Requests</h4>
            <p><i>"anonFirstYr23" wants to connect. Topic: DSA</i></p>
            <button class='accept-button'>Accept</button>
            <button class='reject-button'>Reject</button>
        </div>
        """, unsafe_allow_html=True)

    with col_ask:
        st.markdown("""
        <div class='ask-box'>
            <h4>🧠 Ask a Senior</h4>
            <p><i>"What to study for placement in 2nd year?"</i></p>
            <button class='submit-button'>Answer Question</button>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### Ask Your Question")
    user_q = st.text_area("Type your question here...", key="final_question")
    st.button("Submit Anonymous Question", type="secondary")