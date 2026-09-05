"""
InfraBot - Streamlit chat UI.
Run with: streamlit run ui/app.py
"""
import streamlit as st
import uuid
from agent.agent import build_agent, run_agent

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="InfraBot",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 InfraBot")
st.caption("AI-powered infrastructure assistant — ask me anything about your AWS environment.")

# ── Session state setup ───────────────────────────────────────────────────────
if "agent" not in st.session_state:
    with st.spinner("Starting InfraBot..."):
        try:
            st.session_state.agent = build_agent()
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.messages = []
        except EnvironmentError as e:
            st.error(f"⚠️ Setup error: {e}")
            st.stop()

# ── Render chat history ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Example prompts (shown when chat is empty) ────────────────────────────────
if not st.session_state.messages:
    st.markdown("**Try asking:**")
    examples = [
        "List all my S3 buckets and flag any that are public",
        "Show me all IAM roles in my account",
        "Analyse the IAM role named 'my-role' for security issues",
        "List EC2 instances in us-east-1",
    ]
    cols = st.columns(2)
    for i, example in enumerate(examples):
        if cols[i % 2].button(example, key=f"ex_{i}"):
            st.session_state.pending_prompt = example
            st.rerun()

# ── Handle example button click ───────────────────────────────────────────────
if "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("InfraBot is querying your infrastructure..."):
            response = run_agent(
                st.session_state.agent,
                prompt,
                thread_id=st.session_state.thread_id,
            )
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about your infrastructure..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("InfraBot is querying your infrastructure..."):
            response = run_agent(
                st.session_state.agent,
                prompt,
                thread_id=st.session_state.thread_id,
            )
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ InfraBot")
    st.markdown("**Connected:** AWS (S3, IAM, EC2)")
    st.markdown("**Coming soon:** GCP, CloudWatch logs, Terraform plan analyser")
    st.divider()
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()
    st.divider()
    st.markdown("**Day 1** of InfraBot build")
    st.markdown("[GitHub](https://github.com/ShaikVasid/infra-agent)")
