"""
InfraBot - Streamlit chat UI
Run with: streamlit run ui/app.py
"""
import warnings
warnings.filterwarnings("ignore")

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from agent.agent import build_agent, run_agent

st.set_page_config(
    page_title="InfraBot",
    page_icon="🤖",
    layout="centered"
)

st.markdown("""
<style>
    .main-header { text-align: center; padding: 1rem 0 0.5rem 0; }
    .stChatMessage { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-header'>", unsafe_allow_html=True)
st.title("🤖 InfraBot")
st.caption("Cloud infrastructure assistant — ask about your AWS and GCP environment")
st.markdown("</div>", unsafe_allow_html=True)

# Initialize agent once per session
if "agent" not in st.session_state:
    with st.spinner("Starting InfraBot..."):
        st.session_state.agent = build_agent()
    st.session_state.messages = []
    st.session_state.thread_id = "streamlit-session"

with st.sidebar:
    st.header("⚙️ InfraBot")
    st.markdown("**Status:** 🟢 Connected")
    st.markdown("**LLM:** Google Gemini")
    st.markdown("**Cloud:** AWS + GCP (read-only)")
    st.divider()

    st.subheader("💡 Quick Prompts")
    prompts = [
        "List my S3 buckets",
        "List my IAM roles",
        "List my EC2 instances",
        "Audit my infrastructure",
        "Check vaultpay-2026 bucket",
        "Analyze IAM role AdministratorAccess",
    ]
    for prompt in prompts:
        if st.button(prompt, key=f"btn_{prompt}", use_container_width=True):
            st.session_state.pending_prompt = prompt

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = f"streamlit-{id(st.session_state)}"
        st.rerun()

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Get input — either from sidebar button or chat box
if "pending_prompt" in st.session_state:
    user_input = st.session_state.pop("pending_prompt")
else:
    user_input = st.chat_input("Ask about your infrastructure...")


def clean(response) -> str:
    """Normalize agent response to a plain string."""
    if isinstance(response, str):
        return response
    if isinstance(response, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in response)
    return str(response)


if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = run_agent(
                st.session_state.agent,
                user_input,
                thread_id=st.session_state.thread_id
            )
            response = clean(response)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
