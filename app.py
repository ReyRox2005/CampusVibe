import streamlit as st
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
import os

# --- RAG AND LLM IMPORTS ---
from llama_index.llms.groq import Groq
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# --- Initialization Function (MongoDB) ---
@st.cache_resource
def init_mongo_connection():
    try:
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
            "_id": email, "name": name, "password": password, "created_at": datetime.datetime.now()
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

# ---------------- RAG INITIALIZATION (REPAIRED) ----------------
try:
    groq_key = st.secrets["GROQ_API_KEY"]
    
    # Using Llama 3 via Groq for high-speed, 404-free inference
    LLM_MODEL_INSTANCE = Groq(
        model="llama-3.3-70b-versatile", 
        api_key=groq_key
    )
    
    # Embeddings stay on Hugging Face (Lightweight & Free)
    EMBED_MODEL_INSTANCE = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    Settings.llm = LLM_MODEL_INSTANCE
    Settings.embed_model = EMBED_MODEL_INSTANCE
    
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
        return index.as_query_engine(llm=llm_instance)
    except Exception as e:
        st.sidebar.error(f"RAG Load Error: {e}")
        return None

rag_query_engine = init_rag_engine(LLM_MODEL_INSTANCE)

# ---------------- Session & UI ----------------
if "messages" not in st.session_state: st.session_state.messages = []
if "auth" not in st.session_state: st.session_state.auth = False

st.set_page_config(page_title="CampusVibe", layout="wide")

# --- LOGIN / REGISTRATION LOGIC ---
if not st.session_state.auth:
    st.title("🎓 CampusVibe")
    tab1, tab2 = st.tabs(["Sign In", "Register"])
    with tab1:
        with st.form("login"):
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                ok, msg = login_user(e, p)
                if ok:
                    st.session_state.auth, st.session_state.user_name, st.session_state.user_email = True, msg, e
                    st.rerun()
                else: st.error(msg)
    with tab2:
        with st.form("reg"):
            n = st.text_input("Name")
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Register"):
                ok, msg = register_user(e, p, n)
                st.success(msg) if ok else st.error(msg)
else:
    # --- DASHBOARD UI ---
    st.sidebar.write(f"Logged in as: {st.session_state.user_name}")
    if st.sidebar.button("Logout"): 
        st.session_state.auth = False
        st.rerun()

    st.markdown("## 🔥 Trending Notes")
    # ... (Your trending notes display code here) ...

    # --- AI CHAT SECTION ---
    st.markdown("---")
    st.markdown("## 🧠 Ask the AI Senior")
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if p := st.chat_input("Ask about your notes..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        with st.chat_message("assistant"):
            if rag_query_engine:
                try:
                    with st.spinner("AI Senior is thinking..."):
                        response = rag_query_engine.query(p)
                        ans = str(response)
                        st.markdown(ans)
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                except Exception as e:
                    st.error(f"AI Error: {e}")
            else:
                st.error("AI engine is offline. Check storage folder and API keys.")
