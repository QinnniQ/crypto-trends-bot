Crypto Trends Bot

Answer crypto market questions by blending retrieved insights from transcripts/articles/reddit/substack with live market data. Built with LangChain + Chroma, designed for voice/text input, and ready for a clean UI + deployment.

What it does

Retrieval‑Augmented Answers (RAG): pulls the most relevant snippets from transcripts/articles (and Reddit/Substack) and cites sources.

Live market checks: fetches prices and trending coins (CoinGecko), designed to expand with more tools.

Multi‑tool agent: chooses the right tool (RAG vs. price vs. trending vs. scrapers) per question.

Extensible & deployment‑ready: simple structure, .env‑based secrets, and a planned Streamlit UI.

Repository layout

Current repo is intentionally minimal to avoid breaking a working setup. A gentle refactor plan is included at the end.

crypto-trends-bot/
├─ agent.py                  # main agent entry (terminal)
├─ rag_tool.py               # RAG retrieval helpers
├─ retriever_tool.py         # vector store + retriever utilities
├─ coingecko_tool.py         # price/trending access (extendable)
├─ scrape_*.py / chunk_*.py  # ingestion scripts (reddit/substack/articles)
├─ ui/                       # UI code (e.g., Streamlit app)
├─ data/                     # data/transcripts/vector stores (local, gitignored)
│  └─ transcripts/           # text transcripts (optional)
├─ articles/                 # raw/cleaned article dumps (gitignored)
├─ reddit_data/              # reddit JSON dumps (gitignored)
├─ .env.example              # template for secrets
├─ .gitignore                # keeps secrets/artifacts out of Git
└─ README.md

Quickstart (Windows • PowerShell • VS Code)

1) Clone & enter the folder

# in VS Code Terminal (PowerShell)
git clone https://github.com/<you>/crypto-trends-bot.git
cd crypto-trends-bot

2) Create environment & install deps

# Conda (recommended)
conda create -n crypto-bot python=3.11 -y
conda activate crypto-bot

# Or venv (built‑in)
# py -3.11 -m venv .venv; .\.venv\Scripts\activate

pip install -r requirements.txt

3) Set your secrets

# copy the template and fill your keys
Copy-Item .env.example .env
# then edit .env in VS Code and set:
# OPENAI_API_KEY=...
# REDDIT_CLIENT_ID=...
# REDDIT_SECRET=...

4) Run the agent in the terminal

python agent.py
# Try: "What’s the latest sentiment on BTC from recent sources?"

If you prefer a UI, see Run a minimal UI below.

Ingestion (optional but recommended)

These scripts fetch and prepare content for RAG.

# Substack links → JSON
python scrape_substack_links.py

# (Optional) Full Substack content
python scrape_substack_full_content.py

# Reddit posts → JSON
python scrape_reddit.py

# Chunk and embed into ChromaDB (persisted under data/)
python chunk_articles.py
python chunk_reddit.py
# (If you have transcripts) place them in data/transcripts and run your embed step



How to use the agent (examples)

The agent routes queries to tools depending on intent.

RAG question: “Summarize recent L2 scaling takes from Bankless.”

Live price: “What’s ETH right now and 24h change?”

Trending: “Show me CoinGecko trending coins and any headlines from Substack/Reddit.”

Mixed: “Today’s BTC sentiment across my sources, plus price context.”

The response includes a short answer + sources, and (when enabled) live price/trending snippets.

Environment variables

Create a local .env (never commit secrets):

OPENAI_API_KEY=sk-...
REDDIT_CLIENT_ID=...
REDDIT_SECRET=...

Optional later: COINGECKO_API_KEY (if/when you switch to pro endpoints), LANGCHAIN_TRACING_V2, etc.

Troubleshooting

PowerShell vs Bash: Windows PowerShell does not support << EOF heredocs. Use the commands exactly as written here.

Wrong folder: If python agent.py says “file not found”, run pwd and ensure it ends with your repo folder.

Git made my home a repo: If git rev-parse --show-toplevel prints C:\Users\..., rename the hidden .git in your home: Rename-Item -Force .git .git_backup_home.

Chroma path issues: Use absolute/Path joins and persist under data/.

Roadmap



Dev workflow (safe branching)

# keep main clean
git checkout -b feature/ui
# do work → commit → push → PR into main

Acknowledgements

OpenAI (LLMs, Whisper planned), LangChain (RAG, tools), CoinGecko (market data)

Community sources: Bankless, Coin Bureau, Reddit (for public content)



📚 Ironhack Final Project mapping (how this meets the brief)

Multimodal: text now; voice planned via Whisper.

RAG: Chroma + LangChain retrieval over transcripts/articles.

Agents & tools: RAG tool, price/trending tool, scrapers; memory planned.

LangSmith: planned for evaluation and traces.

Deployment: Streamlit UI + API target; GitHub-first workflow for easy hosting.

