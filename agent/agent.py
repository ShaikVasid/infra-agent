"""
InfraBot - LangGraph agent.
Uses a ReAct loop: Reason → Act (call a tool) → Observe → repeat until done.
"""
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from agent.tools.aws_tools import ALL_TOOLS
from agent.tools.gcp_tools import ALL_GCP_TOOLS

load_dotenv()

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are InfraBot, an AI assistant for cloud infrastructure.
You have access to tools that can query live AWS infrastructure (S3, IAM, EC2).

Your job is to:
1. Answer questions about the user's cloud infrastructure clearly and concisely
2. Flag security issues (public S3 buckets, wildcard IAM permissions, etc.)
3. Suggest specific fixes when you find problems
4. Be honest when you don't have enough info — ask the user to clarify

Always:
- Use tools to get real data before answering (don't guess)
- Explain what you found in plain English, not just raw API output
- Highlight ⚠️ warnings and 🚨 critical issues clearly

You are connected to AWS (S3, IAM, EC2) and GCP (Cloud Storage, IAM). Use the right tools for each cloud.
"""


def build_agent():
    """Build and return the LangGraph ReAct agent with memory."""

    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=0,
            max_tokens=4096,
        )
    elif os.getenv("GOOGLE_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
    elif os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
    elif os.getenv("GOOGLE_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
    else:
        raise EnvironmentError(
            "No LLM API key found. Set one of: ANTHROPIC_API_KEY, GROQ_API_KEY, "
            "OPENAI_API_KEY, or GOOGLE_API_KEY in your .env file."
        )

    memory = MemorySaver()

    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS + ALL_GCP_TOOLS,
        checkpointer=memory,
        prompt=SYSTEM_PROMPT,
    )

    return agent


def run_agent(agent, user_message: str, thread_id: str = "default") -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config=config,
    )
    content = result["messages"][-1].content
    if isinstance(content, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return content
