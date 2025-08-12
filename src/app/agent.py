import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.tools import Tool

from tools.coingecko_tool import CoinGeckoTool
from tools.rag_tool import RagTool
from tools.retriever_tool import RetrieverTool
import os
from dotenv import load_dotenv
load_dotenv()

# LLM setup
llm = ChatOpenAI(temperature=0.2, model="gpt-4")

# Combine both tools
tools = [rag_tool, coingecko_tool]

# Create the agent
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Run in CLI loop
if __name__ == "__main__":
    while True:
        user_input = input("\n🧠 Ask your crypto question: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        response = agent.run(user_input)
        print(f"\n🗨️ Answer:\n{response}")
