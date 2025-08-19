# src/backend/server.py
import os
import re
import time
import logging
from pathlib import Path
from typing import Union, Dict, Any, List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)

from pydantic import BaseModel, Field
from langserve import add_routes
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda

from pycoingecko import CoinGeckoAPI
import requests

# OpenAI (for Whisper transcription)
from openai import OpenAI

# Optional robust imports for your tools (works whether package is 'src.tools' or 'tools')
def _import_tool(modpath, name):
    try:
        return __import__(modpath, fromlist=[name]).__dict__[name]
    except Exception:
        return __import__(modpath.replace("src.", ""), fromlist=[name]).__dict__[name]

# ---------- ENV ----------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # required by ChatOpenAI + Whisper
MODEL = os.getenv("MODEL", "gpt-4o-mini")

# ---------- APP & CORS ----------
app = FastAPI(title="Crypto Trends Bot Backend", version="0.5.0")
_allowed = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:8501,http://127.0.0.1:8501,http://localhost:3000,http://127.0.0.1:3000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed] if _allowed else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

log = logging.getLogger("uvicorn")
cg = CoinGeckoAPI()
HTTP_TIMEOUT = (5, 25)

# OpenAI client (Whisper)
client = OpenAI()  # uses OPENAI_API_KEY from env

# ---------- SYMBOL/ID RESOLUTION for endpoints ----------
TICKER_TO_ID: Dict[str, str] = {
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "sol": "solana",   "solana": "solana",
}
ID_TO_TICKER: Dict[str, str] = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}

_COINS_CACHE_TS = 0.0
_COINS_TTL_SEC = 6 * 60 * 60

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", s.strip().lower())

def _load_coins_list(force: bool = False) -> None:
    global _COINS_CACHE_TS
    now = time.time()
    if not force and (now - _COINS_CACHE_TS) < _COINS_TTL_SEC and len(TICKER_TO_ID) > 3:
        return
    try:
        coins = cg.get_coins_list()
        for c in coins:
            cid = _norm(c.get("id", ""))
            sym = _norm(c.get("symbol", ""))
            if not cid or not sym:
                continue
            ID_TO_TICKER.setdefault(cid, sym.upper())
            TICKER_TO_ID.setdefault(sym, cid)
            TICKER_TO_ID.setdefault(cid, cid)
        _COINS_CACHE_TS = now
        log.info(f"🪙 Coins cache loaded (tickers: {len(TICKER_TO_ID)}).")
    except Exception as e:
        log.warning(f"⚠️ Could not refresh coins list: {e}")

def resolve_coin_id(asset: str) -> str:
    a = _norm(asset)
    if a in TICKER_TO_ID:
        return TICKER_TO_ID[a]
    _load_coins_list(force=True)
    if a in TICKER_TO_ID:
        return TICKER_TO_ID[a]
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{a}",
            params={"localization": "false", "tickers": "false", "market_data": "false"},
            timeout=HTTP_TIMEOUT,
        )
        if r.status_code == 200:
            TICKER_TO_ID.setdefault(a, a)
            ID_TO_TICKER.setdefault(a, a.upper())
            return a
    except Exception:
        pass
    raise HTTPException(status_code=404, detail=f"Unknown asset '{asset}'.")

# ---------- PUBLIC ENDPOINTS ----------
@app.on_event("startup")
def on_startup():
    log.info(f"🔧 Loaded server module: {Path(__file__).resolve()}")
    _load_coins_list(force=True)
    for r in app.routes:
        try:
            methods = sorted(r.methods) if r.methods else []
            log.info(f"➡️  Route: {methods} {r.path}")
        except Exception:
            pass

@app.get("/")
def root():
    return {"service": "crypto-trends-bot-backend", "version": app.version,
            "routes": [r.path for r in app.routes]}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/healthz")
def healthz(ping: bool = Query(default=False)):
    if ping:
        try:
            r = requests.get("https://api.coingecko.com/api/v3/ping", timeout=HTTP_TIMEOUT)
            r.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"CoinGecko unreachable: {e}")
    return {"ok": True}

@app.get("/price/{symbol}")
def price(symbol: str, vs: str = Query(default="usd")):
    try:
        coin_id = resolve_coin_id(symbol)
        data = cg.get_price(ids=coin_id, vs_currencies=_norm(vs) or "usd", include_24hr_change="true")
        p = data.get(coin_id, {})
        price_v = p.get(_norm(vs)) or p.get("usd")
        if price_v is None:
            return {"ok": False, "error": f"Price not found for '{symbol}' in '{vs}'"}
        return {
            "ok": True,
            "ticker": ID_TO_TICKER.get(coin_id, coin_id.upper()),
            "id": coin_id,
            "currency": _norm(vs) or "usd",
            "price": float(price_v),
            "usd": float(p.get("usd", price_v if (_norm(vs) == "usd") else 0.0)),
            "change_24h": float(p.get(f"{_norm(vs)}_24h_change", p.get("usd_24h_change", 0.0))),
        }
    except HTTPException as he:
        return {"ok": False, "error": he.detail}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/history/{symbol}")
def history(symbol: str, days: int = Query(default=7, ge=1, le=365), vs: str = Query(default="usd")):
    try:
        coin_id = resolve_coin_id(symbol)
        data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency=_norm(vs) or "usd", days=days)
        prices = data.get("prices", [])
        if not prices:
            return {"ok": False, "error": f"No history for '{symbol}'"}
        return {"ok": True, "ticker": ID_TO_TICKER.get(coin_id, coin_id.upper()),
                "id": coin_id, "currency": _norm(vs) or "usd", "days": days, "prices": prices}
    except HTTPException as he:
        return {"ok": False, "error": he.detail}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ---------- AUDIO: /transcribe and /voice-ask ----------
import tempfile, logging
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, File, Form, HTTPException
from openai import OpenAI

client = OpenAI()  # uses OPENAI_API_KEY

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    """
    Multipart upload -> Whisper transcription.
    language: ISO code like 'en' (optional, 'auto' is treated as None).
    """
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio upload.")
        if len(audio_bytes) > 24 * 1024 * 1024:  # ~24 MB safety
            raise HTTPException(status_code=413, detail="Audio too large (>24MB). Try a shorter clip.")

        # Pick a safe suffix based on the uploaded filename (helps Whisper parser)
        ext = (Path(file.filename or "").suffix or "").lower()
        if ext not in (".wav", ".mp3", ".m4a", ".webm", ".ogg"):
            ext = ".wav"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as fh:
                tr = client.audio.transcriptions.create(
                    model=os.getenv("WHISPER_MODEL", "whisper-1"),
                    file=fh,
                    language=None if (language in (None, "", "auto")) else language,
                )
        finally:
            try: Path(tmp_path).unlink(missing_ok=True)
            except Exception: pass

        # v1 OpenAI client returns an object with .text
        text = getattr(tr, "text", None)
        if not text:
            raise RuntimeError(f"Empty Whisper response: {tr!r}")

        return {"ok": True, "text": text}

    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Transcription failed")
        # Surface the real error in the HTTP detail so the UI can show it
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.post("/voice-ask")
async def voice_ask(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    """
    One-shot: transcribe with Whisper, then invoke the agent.
    """
    # 1) Transcribe
    tr = await transcribe_audio(file=file, language=language)
    if not tr.get("ok"):
        raise HTTPException(status_code=500, detail=f"Transcription error: {tr}")
    question = (tr.get("text") or "").strip()
    if not question:
        raise HTTPException(status_code=500, detail="Transcription returned empty text.")

    # 2) Ask the agent
    try:
        result = chain.invoke(question)   # chain defined earlier
        return {"ok": True, "question": question, "answer": str(result)}
    except Exception as e:
        logging.exception("Agent error after transcription")
        raise HTTPException(status_code=500, detail=f"AgentError: {e}")


# ---------- IMPORT YOUR TOOLS ----------
rag_tool = _import_tool("src.tools.rag_tool", "rag_tool")
coingecko_tool = _import_tool("src.tools.coingecko_tool", "coingecko_tool")
polymarket_markets_tool = _import_tool("src.tools.polymarket_tool", "polymarket_markets_tool")
polymarket_paper_trade_tool = _import_tool("src.tools.polymarket_tool", "polymarket_paper_trade_tool")
TOOLS = [rag_tool, coingecko_tool, polymarket_markets_tool, polymarket_paper_trade_tool]

# (Legacy example kept; not used directly below)
llm_legacy = ChatOpenAI(model=MODEL, temperature=0).bind_tools(TOOLS)
prompt_legacy = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful Crypto Trends assistant. "
     "Use CoinGecko for prices. "
     "Use CryptoTranscriptRetriever for Reddit/Substack/transcripts. "
     "Use PolymarketMarketSearch to find relevant Polymarket markets. "
     "Use PolymarketPaperTrade for simulation only (no real orders). "
     "Always show short reasoning and include source titles/URLs when you used RAG or Polymarket."),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])
agent_legacy = create_tool_calling_agent(llm_legacy, TOOLS, prompt_legacy)
agent_executor_legacy = AgentExecutor(agent=agent_legacy, tools=TOOLS, verbose=False)

# ---------- AGENT (LangServe) ----------
llm = ChatOpenAI(model=MODEL, temperature=0).bind_tools([rag_tool, coingecko_tool])

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful Crypto Trends assistant. "
     "For market/price questions, use the CoinGecko tool. "
     "For content/narrative questions (Reddit/Substack/transcripts), use the CryptoTranscriptRetriever tool. "
     "Return concise answers and include the retrieved source titles/URLs when available."),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, [rag_tool, coingecko_tool], prompt)
agent_executor = AgentExecutor(agent=agent, tools=[rag_tool, coingecko_tool], verbose=False)

class Ask(BaseModel):
    question: str = Field(..., description="Your question",
                          examples=["What is Reddit saying about BTC right now?"])

def normalize(ask: Union[Ask, Dict[str, Any], str]) -> Dict[str, str]:
    """
    Normalize various inputs to the agent's expected dict shape {'input': <text>}.
    We accept Ask(question), raw string, or dicts with keys 'question' or 'input'.
    """
    q = None
    if isinstance(ask, Ask):
        q = ask.question
    elif isinstance(ask, str):
        q = ask
    elif isinstance(ask, dict):
        q = ask.get("question") or ask.get("input")
        if isinstance(q, dict):
            q = q.get("question") or q.get("input")
    if not isinstance(q, str) or not q.strip():
        raise ValueError("Please provide a non-empty question.")
    return {"input": q}

def pick_output(result: Any) -> str:
    if isinstance(result, dict) and "output" in result:
        out = result["output"]
        if isinstance(out, dict) and "output" in out:
            return str(out["output"])
        return str(out)
    return str(result)

chain = RunnableLambda(normalize) | agent_executor | RunnableLambda(pick_output)

# LangServe routes:
# Use input_type=str so POST /crypto-bot/invoke takes {"input": "your question"} (no more 422).
router = APIRouter()
add_routes(router, chain, path="/crypto-bot", input_type=str)  # also gives /crypto-bot/playground
app.include_router(router, include_in_schema=False)
