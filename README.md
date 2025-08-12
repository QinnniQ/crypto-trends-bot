Crypto Trends Bot
A multimodal cryptocurrency assistant that blends historical insights with live market data.
Ask about specific coins, market sentiment, or expert takes, and get answers backed by curated sources.

Features
Retrieval-Augmented Generation (RAG) for context-rich answers from:

Transcripts of YouTube videos, Substack newsletters, Reddit threads

Live market data via CoinGecko API (price, 24h change, etc.)

Multiple tools in one agent (retrieval + market data fetching)

Conversational interface in the terminal

Designed for expansion — add more tools, more data sources, or a web UI

How it Works
Ingest expert crypto content into a Chroma vector database

Use LangChain to retrieve relevant chunks for a user’s query

Combine retrieved context with LLM reasoning for answers

Supplement with live CoinGecko price data when requested

Quick Start
Clone this repo

Create a .env file in the repo root (see .env.example)

Install dependencies:

bash
Copy
Edit
pip install -r requirements.txt
Add src to your PYTHONPATH and run:

bash
Copy
Edit
$env:PYTHONPATH = (Resolve-Path .\src)
python src\app\agent.py
Example Queries
vbnet
Copy
Edit
🧠 price of btc
🧠 what's reddit saying about solana?
🧠 what did Coin Bureau say about ethereum scaling?
Tech Stack
LangChain for orchestration

OpenAI API for LLM responses

CoinGecko API for live market data

Chroma for vector storage

Python for everything else