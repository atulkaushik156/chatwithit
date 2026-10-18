import os
import uuid
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Stateful Groq Agent", page_icon="🧠", layout="wide")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "threads" not in st.session_state:
    st.session_state.threads = []

with st.sidebar:
    st.title("🔐 API Key Login")
    st.caption("Enter your Groq API key to load your previous chats or start a fresh workspace.")

    api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")

    model = st.selectbox(
        "Model",
        ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"]
    )

    if st.button("Connect / Load History", use_container_width=True, type="primary"):
        try:
            res = requests.post(
                f"{BACKEND_URL}/login-and-threads",
                json={"api_key": api_key},
                timeout=30
            )
            if res.status_code == 200:
                data = res.json()
                st.session_state.authenticated = True
                st.session_state.threads = data["threads"]
                st.session_state.user_id = data["user_id"]
                if data["threads"]:
                    latest_tid = data["threads"][0]["thread_id"]
                    st.session_state.thread_id = latest_tid
                    hist_res = requests.post(
                        f"{BACKEND_URL}/threads/{latest_tid}/history",
                        json={"api_key": api_key},
                        timeout=30
                    )
                    st.session_state.messages = hist_res.json().get("messages", [])
                else:
                    st.session_state.thread_id = str(uuid.uuid4())
                    st.session_state.messages = []
                st.rerun()
            else:
                st.error(res.json().get("detail", "Login failed"))
        except requests.exceptions.RequestException as e:
            st.error(f"Cannot reach backend at {BACKEND_URL}: {e}")

    if st.session_state.authenticated:
        st.divider()
        st.caption(f"Workspace ID: `{st.session_state.user_id}`")
        
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()

        st.subheader("Previous Chats")
        for t in st.session_state.threads:
            is_active = t["thread_id"] == st.session_state.thread_id
            btn_label = f"🟢 {t['title']}" if is_active else f"💬 {t['title']}"
            if st.button(btn_label, key=t["thread_id"], use_container_width=True):
                st.session_state.thread_id = t["thread_id"]
                hist_res = requests.post(
                    f"{BACKEND_URL}/threads/{t['thread_id']}/history",
                    json={"api_key": api_key},
                    timeout=30
                )
                st.session_state.messages = hist_res.json().get("messages", [])
                st.rerun()

st.subheader(f"Thread ID: `{st.session_state.thread_id}`")

if not st.session_state.authenticated:
    st.info("👈 Enter your Groq API Key in the sidebar and click **Connect / Load History** to start.")
    st.stop()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking & saving state to Neon..."):
            try:
                res = requests.post(
                    f"{BACKEND_URL}/chat",
                    json={
                        "api_key": api_key,
                        "thread_id": st.session_state.thread_id,
                        "message": prompt,
                        "model": model
                    },
                    timeout=60
                )
                if res.status_code == 200:
                    reply = res.json()["reply"]
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    
                    threads_res = requests.post(
                        f"{BACKEND_URL}/login-and-threads",
                        json={"api_key": api_key},
                        timeout=30
                    )
                    if threads_res.status_code == 200:
                        st.session_state.threads = threads_res.json()["threads"]
                    st.rerun()
                else:
                    st.error(res.json().get("detail", "Error communicating with backend"))
            except requests.exceptions.RequestException as e:
                st.error(f"Request failed: {e}")