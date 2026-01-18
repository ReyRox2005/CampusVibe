import streamlit as st
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
import os

# --- RAG AND LLM IMPORTS ---
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.settings import Settings
from llama_index.llms.huggingface_api import HuggingFaceInferenceAPI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.storage.docstore.simple_docstore import SimpleDocumentStore
from llama_index.core.storage.index_store.simple_index_store import SimpleIndexStore
from llama_index.core.vector_stores.simple import SimpleVectorStore

# --- Initialization Function (MongoDB) ---
@st.cache_resource
def init_mongo_connection():
    try:
        # Accessing secrets from Streamlit Cloud dashboard
        uri = st.secrets["mongo"]["uri"]
        DB_NAME = st.secrets["mongo"]["database_name"]
        client = MongoClient(uri)
        client.admin.command('ping') 
        database = client[DB_NAME]
        return client, database 
    except Exception as e:
        st.error(f"MongoDB connection error: {e}")
        st.stop()

client, db = init_mongo_connection() 

# ---------------- MongoDB Helpers ----------------
def get_user_collection(): return db["users"] 
def get_notes_collection(): return db["notes"] 

def login_user(email, password):
    user_doc = get_user_collection().find_one({"_id": email})
    if not user_doc: return False, "User not found."
    if user_doc.get("password") == password: return True, user_doc.get("name", email)
    return False, "Invalid password."

def register_user(email, password, name):
    user_coll = get_user_collection()
    if user_coll.find_one({"_id": email}):
        return False, "User already exists with this email."
    try:
        user_coll.insert_one({
            "_id": email,
            "name": name,
            "password": password,
            "created_at": datetime.datetime.now()
        })
        return True, "Registration successful! You can now Sign In."
    except Exception as e:
        return False, f"Error: {e}"

@st.cache_data(ttl=600) 
def get_trending_notes():
    try:
        notes = list(get_notes_collection().find().sort("downloads", pymongo.DESCENDING).limit(3))
        for note in notes:
            if isinstance(note["_id"], ObjectId): note["_id"] = str(note["_id"])
        return notes
    except: return []

def get_specific_resource(subject, year, sem, resource_type, unit_num=None):
    query = {"subject": subject, "year": year, "semester": sem}
    if unit_num: query["unit"] = int(unit_num)
    try:
        return get_notes_collection().find_one(query)
    except: return None

def submit_note_feedback(note_id, user_email, feedback_text):
    if not feedback_text: return False
    new_feedback = {"user_email": user_email, "text": feedback_text, "submitted_at": datetime.datetime.now()}
    try:
        target_id = ObjectId(note_id) if isinstance(note_id, str) and len(note_id) == 24 else note_id
        result = get_notes_collection().update_one({"_id": target_id}, {"$push": {"feedback": new_feedback}})
        return result.modified_count > 0
    except: return False

# ---------------- RAG INITIALIZATION (CLOUD VERSION) ----------------
try:
    # Use HF_TOKEN from Streamlit Secrets
    hf_token = st.secrets.get("NEW_HF_TOKEN", None)
    st.sidebar.write("HF token length:", len(hf_token) if hf_token else "NOT LOADED")
    if not hf_token:
        hf_token = st.secrets.get("HF_TOKEN", None)
    
    # Using TinyLlama via Hugging Face API (Path B)
    LLM_MODEL_INSTANCE = HuggingFaceInferenceAPI(
        model_name="HuggingFaceH4/zephyr-7b-beta",
        token=hf_token
    )
    EMBED_MODEL_INSTANCE = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    Settings.llm, Settings.embed_model = LLM_MODEL_INSTANCE, EMBED_MODEL_INSTANCE
except Exception as e:
    st.sidebar.error(f"AI Setup Error: {e}")
    LLM_MODEL_INSTANCE = None

def init_rag_engine(llm_instance):
    if not llm_instance: return None
    try:
        PERSIST_DIR = "./storage"
        if not os.path.exists(PERSIST_DIR):
            st.sidebar.warning("Storage folder not found. AI will not have note context.")
            return None
            
        storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
        index = load_index_from_storage(storage_context)
        # Streaming with APIs can be tricky, so we use standard query mode for stability
        return index.as_query_engine(llm=llm_instance)
    except Exception as e:
        st.sidebar.error(f"RAG Load Error: {e}")
        return None

rag_query_engine = init_rag_engine(LLM_MODEL_INSTANCE)

# ---------------- Session Defaults ----------------
keys = ["auth", "user_email", "user_name", "filter_applied", "submitted_year", "submitted_sem", "selected_subject_view", "selected_resource_type"]
for key in keys:
    if key not in st.session_state: st.session_state[key] = False if "applied" in key or "auth" in key else None
if "messages" not in st.session_state: st.session_state.messages = []

st.set_page_config(page_title="CampusVibe", layout="wide")

# ---------------- CSS STYLING ----------------
st.markdown("""
    <style>
    .note-card { background-color: #f4f0ff; padding: 1.2rem; border-radius: 12px; margin-bottom: 1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05); height: 260px; border: 1px solid #e0e0e0; display: flex; flex-direction: column; justify-content: center; text-align: center; } 
    .note-title { font-weight: 700; font-size: 1.1rem; color: #2575fc; } 
    .note-info { font-size: 0.92rem; color: #555; }
    </style>
    """, unsafe_allow_html=True)

# ---------------- AUTHENTICATION ----------------
if not st.session_state.auth:
    st.markdown("<h1 style='text-align:center;color:#2575fc;'>CampusVibe</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1]) 
    with col2:
        tab1, tab2 = st.tabs(["🔒 Sign In", "📝 Register"])

        with tab1:
            with st.form("login_form"):
                st.subheader("Sign In")
                email = st.text_input("Email")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("SIGN IN", type="primary", use_container_width=True):
                    ok, msg = login_user(email, pw)
                    if ok:
                        st.session_state.auth, st.session_state.user_email, st.session_state.user_name = True, email, msg
                        st.rerun()
                    else: st.error(msg)

        with tab2:
            with st.form("register_form"):
                st.subheader("Create New Account")
                new_name = st.text_input("Full Name")
                new_email = st.text_input("Email Address")
                new_pw = st.text_input("Create Password", type="password")
                if st.form_submit_button("REGISTER", use_container_width=True):
                    if not new_name or not new_email or not new_pw:
                        st.warning("Please fill all fields.")
                    else:
                        success, msg = register_user(new_email, new_pw, new_name)
                        if success: st.success(msg)
                        else: st.error(msg)

# ---------------- DASHBOARD ----------------
else:
    col_logo, col_search, col_notify = st.columns([2, 6, 1])
    col_logo.markdown("### 🎓 CampusVibe")
    col_search.text_input("Search anything...", label_visibility="collapsed", placeholder="Search for notes...")
    col_notify.markdown("🔔")
    st.markdown("---")

    with st.sidebar:
        st.markdown(f"👋 Welcome, **{st.session_state.user_name}**")
        if st.button("Logout", use_container_width=True): 
            st.session_state.auth = False
            st.rerun()
        st.markdown("### Filters")
        y = st.selectbox("Select Year", ["1st Year", "2nd Year", "3rd Year", "4th Year"])
        s = st.selectbox("Select Semester", ["5th Sem", "6th Sem"] if y == "3rd Year" else ["1st Sem", "2nd Sem"])
        b = st.selectbox("Branch", ["CSE", "ECE", "ME", "CE"])
        if st.button("Submit", use_container_width=True, type="primary"):
            st.session_state.filter_applied, st.session_state.submitted_year, st.session_state.submitted_sem, st.session_state.selected_subject_view, st.session_state.selected_resource_type = True, y, s, None, None
            st.rerun()

    if not st.session_state.filter_applied:
        st.markdown("## 🔥 Trending Notes")
        cols = st.columns(3)
        for i, note in enumerate(get_trending_notes()):
            with cols[i % 3]:
                st.markdown(f"<div class='note-card'><div class='note-title'>📄 {note.get('name')}</div><div class='note-info'>Subject: <b>{note.get('subject')}</b></div></div>", unsafe_allow_html=True)
                st.link_button("⬇️ View/Download", url=note.get("download_url", "#"), use_container_width=True)
                with st.form(key=f"fb_tr_{note['_id']}", clear_on_submit=True):
                    fb_t = st.text_input("Quick Feedback", key=f"it_tr_{note['_id']}")
                    if st.form_submit_button("Submit"): submit_note_feedback(note['_id'], st.session_state.user_email, fb_t); st.success("Sent!")
    else:
        # Subject and Category logic
        if st.session_state.submitted_year == "3rd Year" and st.session_state.submitted_sem == "5th Sem":
            if st.session_state.selected_subject_view and st.session_state.selected_resource_type:
                sub = st.session_state.selected_subject_view
                res_type = st.session_state.selected_resource_type
                st.markdown(f"## {sub} - {res_type}")
                if st.button("⬅️ Back to Categories"): st.session_state.selected_resource_type = None; st.rerun()
                
                cols = st.columns(3)
                if res_type == "Notes":
                    for u_num in range(1, 6):
                        data = get_specific_resource(sub, "3rd Year", "5th Sem", "Notes", u_num)
                        with cols[(u_num-1) % 3]:
                            display_name = data.get('name') if data else f"{sub} Unit {u_num}"
                            drive_url = data.get('download_url', '#') if data else "#"
                            st.markdown(f"<div class='note-card'><div class='note-title'>📄 {display_name}</div><div class='note-info'>Subject: <b>{sub}</b><br>Year: <b>3rd Year</b></div></div>", unsafe_allow_html=True)
                            st.link_button("⬇️ View/Download", url=drive_url, use_container_width=True)
                            with st.form(key=f"fb_u_{sub}_{u_num}", clear_on_submit=True):
                                fb_val = st.text_input("Quick Feedback", key=f"in_u_{sub}_{u_num}")
                                if st.form_submit_button("Submit"):
                                    if data: submit_note_feedback(data['_id'], st.session_state.user_email, fb_val); st.success("Feedback Saved!")
                                    else: st.warning("Resource not found.")
                else:
                    data = get_specific_resource(sub, "3rd Year", "5th Sem", res_type)
                    with cols[0]:
                        if data:
                            st.markdown(f"<div class='note-card'><div class='note-title'>📂 {res_type}</div><div class='note-info'>Subject: <b>{sub}</b></div></div>", unsafe_allow_html=True)
                            st.link_button("⬇️ View/Download", url=data.get('download_url', '#'), use_container_width=True)
                        else: st.info(f"No {res_type} found.")
            elif st.session_state.selected_subject_view:
                sub = st.session_state.selected_subject_view
                st.markdown(f"## {sub} - Select Category")
                if st.button("⬅️ Back to Subjects"): st.session_state.selected_subject_view = None; st.rerun()
                res_types = ["Notes", "PYQ", "Lab File"]
                cols = st.columns(3)
                for i, r_type in enumerate(res_types):
                    with cols[i % 3]:
                        st.markdown(f"<div class='note-card'><div class='note-title'>📂 {r_type}</div></div>", unsafe_allow_html=True)
                        if st.button(f"Open {r_type}", key=f"btn_res_{r_type}", use_container_width=True):
                            st.session_state.selected_resource_type = r_type; st.rerun()
            else:
                st.markdown("## Choose a Subject")
                if st.button("🏠 Back to Home"): st.session_state.filter_applied = False; st.rerun()
                subs = ["OS", "AI", "Computer Networking", "Deep Learning", "NN"]
                cols = st.columns(3)
                for i, s_name in enumerate(subs):
                    with cols[i % 3]:
                        st.markdown(f"<div class='note-card'><div class='note-title'>📄 {s_name}</div></div>", unsafe_allow_html=True)
                        if st.button(f"Select {s_name}", key=f"btn_s_{s_name}", use_container_width=True):
                            st.session_state.selected_subject_view = s_name; st.rerun()
        else:
            st.warning("Notes for this year/semester are yet to be uploaded.")
            if st.button("🏠 Back to Home"): st.session_state.filter_applied = False; st.rerun()

    # --- AI CHAT (Updated for Stability) ---
    st.markdown("---")
    st.markdown("## 🧠 Ask the AI Senior")
    
    # Show history
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if p := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        with st.chat_message("assistant"):
            if rag_query_engine:
                try:
                    # Using a spinner helps the user know the AI is working
                    with st.spinner("AI Senior is thinking..."):
                        response = rag_query_engine.query(p)
                        ans = str(response)
                        st.markdown(ans)
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                except Exception as e:
                    # This captures the Hugging Face "Loading" error specifically
                    if "503" in str(e) or "loading" in str(e).lower():
                        st.info("The AI is waking up! Please wait 30 seconds and click 'Enter' again.")
                    else:
                        st.error(f"AI Error: {e}")
            else:
                st.error("AI engine is offline. Check sidebar for errors.")
