"""
InfraBot CLI — quick way to test the agent without starting Streamlit.
Usage: python3 main.py
"""
import warnings
warnings.filterwarnings("ignore")

from agent.agent import build_agent, run_agent


def clean(response) -> str:
    """Always return a plain string from the agent response."""
    if isinstance(response, str):
        return response
    if isinstance(response, list):
        parts = []
        for p in response:
            if isinstance(p, dict):
                parts.append(p.get("text", ""))
            else:
                parts.append(str(p))
        return "".join(parts)
    return str(response)


def main():
    print("🤖 InfraBot CLI (type 'exit' to quit)\n")
    agent = build_agent()
    thread_id = "cli-session"

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        response = run_agent(agent, user_input, thread_id=thread_id)
        print(f"\nInfraBot: {clean(response)}\n")


if __name__ == "__main__":
    main()
