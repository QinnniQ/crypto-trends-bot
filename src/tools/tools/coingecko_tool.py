from langchain.tools import Tool
import requests
import re

# ⚙️ One-time download and normalized cache
def build_coin_map():
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        coins = response.json()
        print(f"✅ Retrieved {len(coins)} coins from CoinGecko")
        coin_map = {}
        for coin in coins:
            cid = (coin.get("id") or "").strip()
            sym = (coin.get("symbol") or "").strip()
            name = (coin.get("name") or "").strip()
            if not cid:
                continue
            coin_map[cid.lower()] = cid
            if sym:
                coin_map[sym.lower()] = cid
            if name:
                coin_map[name.lower()] = cid
        return coin_map
    except Exception as e:
        print("❌ Failed to fetch CoinGecko coin list:", e)
        return {}

COIN_MAP = build_coin_map()

_OVERRIDES = {
    "eth": "ethereum",
    "ethereum": "ethereum",
    "btc": "bitcoin",
    "bitcoin": "bitcoin",
    "sol": "solana",
    "solana": "solana",
    "link": "chainlink",
    "matic": "matic-network",
}

def _sanitize_to_tokens(text: str):
    """
    Lowercase, strip surrounding quotes/backticks, and split into tokens.
    Works for inputs like: "'btc'", '"ETH"', "price of btc", "`Solana`"
    """
    if not text:
        return []
    s = text.strip().lower()
    # remove surrounding quotes/backticks if present
    s = s.strip("'\"`")
    # split on non-alphanumeric (keep dashes for ids like 'matic-network')
    tokens = re.split(r"[^a-z0-9\-]+", s)
    return [t for t in tokens if t]

def get_coin_id(query: str) -> str:
    tokens = _sanitize_to_tokens(query)

    # 1) fast path: overrides
    for t in tokens:
        if t in _OVERRIDES:
            return _OVERRIDES[t]

    # 2) direct map lookup for any token
    for t in tokens:
        if t in COIN_MAP:
            return COIN_MAP[t]

    # 3) fall back to the whole sanitized string if single token
    if len(tokens) == 1 and tokens[0] in COIN_MAP:
        return COIN_MAP[tokens[0]]

    return ""

def get_crypto_price(query: str) -> str:
    coin_id = get_coin_id(query)
    if not coin_id:
        return f"❌ Couldn't find a coin called '{query}'. Try using the full name or symbol like 'Bitcoin' or 'BTC'."

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"❌ CoinGecko request error: {e}"

    price_info = data.get(coin_id, {})
    price = price_info.get("usd")
    change = price_info.get("usd_24h_change", 0.0)

    if price is None or price == 0:
        return f"⚠️ Could not retrieve a valid USD price for '{query}'. Please try again later."

    return f"The current price of {coin_id.upper()} is ${price:.2f} (24h change: {change:.2f}%)."

coingecko_tool = Tool(
    name="CoinGeckoPriceFetcher",
    func=get_crypto_price,
    description="Use this to get current prices and 24h change for any cryptocurrency. Input can be a coin name or symbol like 'ETH', 'Solana', or 'Shiba Inu'.",
)
