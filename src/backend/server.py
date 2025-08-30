# src/backend/server.py
import os
import re
import time
import logging
from pathlib import Path
from typing import Optional, Dict

from fastapi import FastAPI, APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, find_dotenv

# Third-party
from pycoingecko import CoinGeckoAPI
import requests
from importlib import import_module

# LangChain / Serve
from langserve import add_routes
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda

# OpenAI client (Whisper + chat uses OPENAI_API_KEY)
from openai import OpenAI

# ---------- env / logging ----------
load_dotenv(find_dotenv(), override=False)
log = logging.getLogger("uvicorn")
logging.basicConfig(level=os.getenv("LOGLEVEL", "INFO"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = os.getenv("MODEL", "gpt-4o-mini")

# ---------- app / cors ----------
app = FastAPI(title="Crypto Trends Bot Backend", version="0.6.1")

_allowed = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:8501,http://127.0.0.1:8501,http://localhost:3000,http://127.0.0.1:3000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed if o.strip()] or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- globals ----------
cg = CoinGeckoAPI()
HTTP_TIMEOUT = (8, 30)  # a bit longer to tolerate cold starts
client = OpenAI()       # uses env OPENAI_API_KEY

TICKER_TO_ID: Dict[str, str] = {"btc": "bitcoin", "bitcoin": "bitcoin",
                                "eth": "ethereum", "ethereum": "ethereum",
                                "sol": "solana", "solana": "solana"}
ID_TO_TICKER: Dict[str, str] = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}
_COINS_CACHE_TS = 0.0
_COINS_TTL_SEC = 6 * 60 * 60

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", (s or "").strip().lower())

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
            if cid and sym:
                ID_TO_TICKER.setdefault(cid, sym.upper())
                TICKER_TO_ID.setdefault(sym, cid)
                TICKER_TO_ID.setdefault(cid, cid)
        _COINS_CACHE_TS = now
        log.info("🪙 Coins cache loaded (tickers: %s).", len(TICKER_TO_ID))
    except Exception as e:
        log.warning("⚠️ Could not refresh coins list: %s", e)

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

# ---------- public endpoints ----------
@app.on_event("startup")
def on_startup():
    log.info("🔧 Loaded server: %s", Path(__file__).resolve())
    _load_coins_list(force=True)

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

# ---------- voice: /transcribe + /voice-ask ----------
import tempfile

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio upload.")
        if len(audio_bytes) > 24 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Audio too large (>24MB).")

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

        text = getattr(tr, "text", "") or ""
        if not text.strip():
            raise RuntimeError(f"Empty Whisper response: {tr!r}")
        return {"ok": True, "text": text}

    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Transcription failed")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

@app.post("/voice-ask")
async def voice_ask(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    tr = await transcribe_audio(file=file, language=language)
    if not tr.get("ok"):
        raise HTTPException(status_code=500, detail=f"Transcription error: {tr}")
    question = (tr.get("text") or "").strip()
    if not question:
        raise HTTPException(status_code=500, detail="Transcription returned empty text.")
    try:
        result = CHAIN.invoke(question)
        return {"ok": True, "question": question, "answer": str(result)}
    except Exception as e:
        logging.exception("Agent error after transcription")
        raise HTTPException(status_code=500, detail=f"AgentError: {e}")

# ---------- optional tools (safe import) ----------
def _safe_import_tool(modpath: str, name: str):
    try:
        module = import_module(modpath)
        return getattr(module, name)
    except Exception as e:
        logging.warning("Tool %s from %s unavailable: %s", name, modpath, e)
        return None

RAG_TOOL      = _safe_import_tool("src.tools.rag_tool", "rag_tool")
COINGECKO_EXT = _safe_import_tool("src.tools.coingecko_tool", "coingecko_tool")
POLY_MARKETS  = _safe_import_tool("src.tools.polymarket_tool", "polymarket_markets_tool")
POLY_PAPER    = _safe_import_tool("src.tools.polymarket_tool", "polymarket_paper_trade_tool")

# ---------- builtin CoinGecko tool (fallback) ----------
@tool("coingecko_price", return_direct=False)
def coingecko_price(symbol: str, vs: str = "usd") -> str:
    try:
        coin_id = resolve_coin_id(symbol)
        data = cg.get_price(ids=coin_id, vs_currencies=_norm(vs) or "usd", include_24hr_change="true")
        p = data.get(coin_id, {})
        price_v = p.get(_norm(vs)) or p.get("usd")
        chg = p.get(f"{_norm(vs)}_24h_change", p.get("usd_24h_change", 0.0))
        return f"{ID_TO_TICKER.get(coin_id, coin_id.upper())}/{_norm(vs).upper()}: {float(price_v):,.4f} ({float(chg):+.2f}% 24h)"
    except Exception as e:
        return f"Error getting price for {symbol}: {e}"

TOOLS = []
TOOLS.append(COINGECKO_EXT or coingecko_price)
if RAG_TOOL: TOOLS.append(RAG_TOOL)
for t in (POLY_MARKETS, POLY_PAPER):
    if t: TOOLS.append(t)

logging.info("Activated tools: %s", [getattr(t, 'name', getattr(t, '__name__', 'tool')) for t in TOOLS])

# ---------- agent / chain ----------
SYSTEM_TEXT = (
    "You are a helpful Crypto Trends assistant. "
    "Use the CoinGecko tool for spot prices and simple market facts. "
    "If a transcript retrieval tool is available, use it for narratives and include source titles/URLs. "
    "Keep answers concise."
)

CHAT = ChatOpenAI(model=MODEL, temperature=0)
if TOOLS:
    PROMPT = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_TEXT),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    AGENT = create_tool_calling_agent(CHAT.bind_tools(TOOLS), TOOLS, PROMPT)
    EXECUTOR = AgentExecutor(agent=AGENT, tools=TOOLS, verbose=False)
    CHAIN = RunnableLambda(lambda x: {"input": x}) | EXECUTOR | RunnableLambda(lambda x: x.get("output", x))
else:
    PROMPT = ChatPromptTemplate.from_messages([("system", SYSTEM_TEXT), ("human", "{input}")])
    CHAIN = PROMPT | CHAT | RunnableLambda(lambda m: getattr(m, "content", str(m)))

router = APIRouter()
add_routes(router, CHAIN, path="/crypto-bot", input_type=str)
app.include_router(router, include_in_schema=False)
