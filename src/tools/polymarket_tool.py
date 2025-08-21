# src/tools/polymarket_tool.py
import os, re, requests, math
from typing import List, Dict
from langchain.tools import Tool

GAMMA = os.getenv("POLYMARKET_GAMMA", "https://gamma-api.polymarket.com").rstrip("/")

def _norm(q: str) -> str:
    return re.sub(r"\s+", " ", q).strip()

def search_markets(query: str, limit: int = 10) -> str:
    """
    Search Polymarket markets via Gamma API (read-only).
    Returns a concise, human-readable list with links & implied probs.
    """
    q = _norm(query)
    try:
        r = requests.get(f"{GAMMA}/markets", timeout=15)
        r.raise_for_status()
        markets = r.json()
    except Exception as e:
        return f"❌ Polymarket (Gamma) error: {e}"

    # naive filter by question text/category
    ql = q.lower()
    hits: List[Dict] = [
        m for m in markets
        if ql in (m.get("question", "") or "").lower()
           or ql in (m.get("category", "") or "").lower()
    ][:limit]

    if not hits:
        return f"No Polymarket markets matched: “{q}”. (Total fetched: {len(markets)})"

    lines = [f"Top matches for **{q}**:"]
    for i, m in enumerate(hits, 1):
        qtext = m.get("question", "Untitled")
        url = m.get("url") or f"https://polymarket.com/event/{m.get('slug','')}"
        # try to show best bid/ask -> midpoint probability if available
        # some Gamma payloads include 'outcomes' with prices in 'yesPrice'/'noPrice'
        yes = m.get("yesPrice") or (m.get("outcomes") or [{}])[0].get("price")
        prob = None
        try:
            if yes is not None:
                prob = float(yes)
        except Exception:
            pass
        tag = f" ~ {prob*100:.1f}%" if isinstance(prob, float) else ""
        lines.append(f"{i}. {qtext}{tag}\n   {url}")
    return "\n".join(lines)

polymarket_markets_tool = Tool(
    name="PolymarketMarketSearch",
    func=search_markets,
    description=("Search Polymarket markets by keyword and return matches with links and implied probabilities. "
                 "Use for discovery: e.g., 'US election', 'BTC ETF', 'Ethereum upgrade'.")
)

# ---- Optional: paper-trade stub (no real orders) ----
def paper_trade(instruction: str, max_size_usdc: float = 10.0) -> str:
    """
    Simulate an order decision; DOES NOT place real trades.
    Parses a simple intent like: 'Buy YES 5 USDC on <market url or slug>'.
    """
    msg = instruction.strip()
    # super basic parse
    side = "BUY YES" if "buy" in msg.lower() and "no" not in msg.lower() else \
           ("BUY NO" if "buy" in msg.lower() else "HOLD")
    size = min(max_size_usdc, 10.0)
    return f"🧪 PAPER TRADE: {side} ~{size} USDC (simulation only). Instruction: {instruction}"

polymarket_paper_trade_tool = Tool(
    name="PolymarketPaperTrade",
    func=paper_trade,
    description=("Simulate a Polymarket order (no execution). Input: plain English intent, "
                 "e.g., 'Buy YES 5 USDC on US election popular vote market'.")
)
