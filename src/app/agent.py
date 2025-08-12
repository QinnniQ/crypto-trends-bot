import sys, os, pathlib
# Make "src" importable when running this file directly
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()  # needs OPENAI_API_KEY in your .env

# --- LangChain imports (with backwards-compat safety) ---
try:
    # Newer way
    from langchain_openai import ChatOpenAI
except Exception:
    # Older way (still works in many setups)
    from langchain.chat_models import ChatOpenAI

from langchain.agents import initialize_agent, AgentType

# --- Your Tool objects (already built in your tool files) ---
from tools.rag_tool import rag_tool
from tools.coingecko_tool import coingecko_tool


def build_agent():
    llm = ChatOpenAI(temperature=0.2, model="gpt-4")
    tools = [rag_tool, coingecko_tool]

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
    )
    return agent


def main():
    agent = build_agent()
    print("✅ Agent ready. Type 'exit' to quit.")
    while True:
        q = input("\n🧠 Ask your crypto question: ")
        if q.strip().lower() in {"exit", "quit"}:
            break
        try:
            ans = agent.run(q)
            print(f"\n🗨️ Answer:\n{ans}")
        except Exception as e:
            print("❌ Error while running the agent:", e)


if __name__ == "__main__":
    main()
