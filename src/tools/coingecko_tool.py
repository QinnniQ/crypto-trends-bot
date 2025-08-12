from langchain.tools import Tool
import requests

# ⚙️ One-time download and normalized cache
def build_coin_map():
    url = "https://api.coingecko.com/api/v3/coins/list"
    try:
        response = requests.get(url)
        coins = response.json()
        print(f"✅ Retrieved {len(coins)} coins from CoinGecko")
        coin_map = {}
        for coin in coins:
            coin_map[coin["id"].lower()] = coin["id"]
            coin_map[coin["symbol"].lower()] = coin["id"]
            coin_map[coin["name"].lower()] = coin["id"]
        return coin_map
    except Exception as e:
        print("❌ Failed to fetch CoinGecko coin list:", e)
        return {}

COIN_MAP = build_coin_map()

def get_coin_id(query: str) -> str:
    query = query.strip().lower()

    # Hardcoded fixes for ambiguous or failing coins
    overrides = {
        "eth": "ethereum",
        "ethereum": "ethereum",
        "btc": "bitcoin",
        "bitcoin": "bitcoin",
        "sol": "solana",
        "solana": "solana",
        "link": "chainlink",
        "matic": "matic-network",
    }

    if query in overrides:
        return overrides[query]

    return COIN_MAP.get(query)



def get_crypto_price(query: str) -> str:
    coin_id = get_coin_id(query)
    if not coin_id:
        return f"❌ Couldn't find a coin called '{query}'. Try using the full name or symbol like 'Bitcoin' or 'BTC'."

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return "❌ CoinGecko API failed."

    data = response.json()
    price_info = data.get(coin_id, {})

    price = price_info.get("usd", None)
    change = price_info.get("usd_24h_change", 0.0)

    if price is None or price == 0:
        return f"⚠️ Could not retrieve a valid USD price for '{query.title()}'. Please try again later."

    return f"The current price of {query.upper()} is ${price:.2f} (24h change: {change:.2f}%)."


coingecko_tool = Tool(
    name="CoinGeckoPriceFetcher",
    func=get_crypto_price,
    description="Use this to get current prices and 24h change for any cryptocurrency. Input can be a coin name or symbol like 'ETH', 'Solana', or 'Shiba Inu'."
)
