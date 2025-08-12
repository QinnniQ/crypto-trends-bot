# Crypto Trends Bot

A multimodal crypto assistant that blends historical insights (RAG over transcripts/news) with live market data from CoinGecko. Ask about specific coins, market sentiment, or expert takes, and get answers backed by curated sources.

## Features
- Retrieval‑Augmented Generation over curated sources (YouTube transcripts, Substack, Reddit)
- Live prices + 24h change via CoinGecko
- Tool‑augmented agent (retrieval + market data)
- Simple CLI for now; web UI later

## How it Works (very short)
1. Ingest expert crypto content into a local Chroma vector DB.  
2. Retrieve relevant chunks for a user’s question via LangChain.  
3. Generate a response with LLM + (optionally) live price tool output.

## Quick Start
1. **Env file** (repo root): create `.env` using `.env.example` as a template
```
OPENAI_API_KEY=your-openai-key
```
2. **Install deps**
```bash
pip install -r requirements.txt
```
3. **Run the agent**
- **Windows (PowerShell)**
```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python srcppgent.py
```
- **macOS/Linux (bash/zsh)**
```bash
export PYTHONPATH=$(pwd)/src
python src/app/agent.py
```

## Example Prompts
```
price of btc
what's reddit saying about solana?
what did Coin Bureau say about ethereum scaling?
```

## Tech Stack
- LangChain (agent/tool orchestration)
- OpenAI (LLM)
- CoinGecko (live prices)
- Chroma (vector store)

## Repo Layout
```
.
├─ src/
│  ├─ app/                # agent entrypoints
│  └─ tools/              # rag_tool, coingecko_tool
├─ chroma_db/             # local vector DB (not tracked except .gitkeep)
├─ data/                  # optional raw/processed data
├─ tests/
├─ .env.example
├─ requirements.txt
└─ README.md
```
