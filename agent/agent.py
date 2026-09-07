"""
InfraBot agent - LangGraph ReAct loop.
Reason -> pick a tool -> call it -> observe result -> repeat until done.
"""
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from agent.tools.aws_tools import ALL_TOOLS
from agent.tools.gcp_tools import ALL_GCP_TOOLS

load_dotenv()

SYSTEM_PROMPT = """You are InfraBot, a cloud infrastructure assistant.
You have live access to AWS (S3, IAM, EC2) and GCP (Cloud Storage, IAM) through tools.

Rules:
- Always call a tool to get real data before answering. Never guess.
- Explain findings in plain English, not raw JSON.
- Flag security issues clearly: use ⚠️ for warnings, 🚨 for critical.
- Suggest a concrete fix whenever you find a problem.
- If you need more info, ask the user to clarify.
"""


def build_agent():
    """Build the ReAct agent. Picks the LLM based on which API key is set."""

    if os.getenv("GOOGLE_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
    elif os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
    elif os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)
    else:
        raise EnvironmentError(
            "No LLM API key found. Set GOOGLE_API_KEY, OPENAI_API_KEY, or "
            "ANTHROPIC_API_KEY in your .env file."
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
    # Gemini sometimes returns a list of content parts instead of a plain string
    if isinstance(content, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return content
