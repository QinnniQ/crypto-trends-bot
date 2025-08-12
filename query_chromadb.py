import os
import requests
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA

# === LOAD ENV VARIABLES ===
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found in environment variables or .env file.")

# === CONFIG ===
CHROMA_DB_DIR = r"C:\Users\nicho\Documents\crypto_bot\chroma_db"

# === INIT EMBEDDINGS & DB ===
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", api_key=OPENAI_API_KEY)
db = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embeddings)
retriever = db.as_retriever(search_kwargs={"k": 8})

# === LLM ===
llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)
qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever, return_source_documents=True)

# === COINGECKO PRICE FETCHER ===
def get_crypto_price(symbol: str):
    """Fetch current price and 24h change for a given crypto symbol."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": symbol.lower(),
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        resp = requests.get(url, params=params)
        data = resp.json()
        if symbol.lower() in data:
            price = data[symbol.lower()]["usd"]
            change = data[symbol.lower()]["usd_24h_change"]
            return f"${price:,.2f} (24h change: {change:.2f}%)"
        return f"❌ Could not fetch price for '{symbol}'."
    except Exception as e:
        return f"⚠ Error fetching price: {e}"

# === DETECT QUERY TYPE ===
def detect_query_type(query: str):
    """Determine if query is about price, analysis, or both."""
    q = query.lower()
    price_keywords = ["price", "current", "worth", "value", "update", "today", "latest"]
    analysis_keywords = ["say", "opinion", "think", "analysis", "view", "news", "report", "insight"]

    price_asked = any(word in q for word in price_keywords)
    analysis_asked = any(word in q for word in analysis_keywords)

    # If query mentions a coin but no explicit price/analysis words → assume hybrid
    coin_names = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "cardano", "ada",
                  "dogecoin", "doge", "xrp", "ripple", "polkadot", "dot", "litecoin", "ltc",
                  "avalanche", "avax", "chainlink", "link", "matic", "polygon", "tron", "trx",
                  "stellar", "xlm", "monero", "xmr"]
    if any(coin in q for coin in coin_names) and not price_asked and not analysis_asked:
        return "hybrid"

    if price_asked and analysis_asked:
        return "hybrid"
    elif price_asked:
        return "price"
    else:
        return "analysis"

# === HANDLE QUERY ===
def handle_query(query: str):
    query_type = detect_query_type(query)

    # Detect coin name and map to CoinGecko ID
    tokens = {
        "bitcoin": "bitcoin", "btc": "bitcoin",
        "ethereum": "ethereum", "eth": "ethereum",
        "solana": "solana", "sol": "solana",
        "cardano": "cardano", "ada": "cardano",
        "dogecoin": "dogecoin", "doge": "dogecoin",
        "xrp": "ripple", "ripple": "ripple",
        "polkadot": "polkadot", "dot": "polkadot",
        "litecoin": "litecoin", "ltc": "litecoin",
        "avalanche": "avalanche-2", "avax": "avalanche-2",
        "chainlink": "chainlink", "link": "chainlink",
        "matic": "polygon", "polygon": "polygon",
        "tron": "tron", "trx": "tron",
        "stellar": "stellar", "xlm": "stellar",
        "monero": "monero", "xmr": "monero"
    }
    coin_symbol = None
    for key, symbol in tokens.items():
        if key in query.lower():
            coin_symbol = symbol
            break

    # Price only
    if query_type == "price":
        if coin_symbol:
            return f"{coin_symbol.upper()} price: {get_crypto_price(coin_symbol)}"
        else:
            return "❌ Please specify a cryptocurrency for price lookup."

    # Analysis only
    if query_type == "analysis":
        result = qa.invoke({"query": query})
        answer = result["result"]
        sources = "\n".join(
            [f"- {doc.metadata.get('title', 'Unknown')} ({doc.metadata.get('url', '')})"
             for doc in result["source_documents"]]
        )
        return f"{answer}\n\n📚 Sources:\n{sources}"

    # Hybrid: Price + Analysis
    if query_type == "hybrid":
        price_info = get_crypto_price(coin_symbol) if coin_symbol else "❌ No coin specified."
        result = qa.invoke({"query": query})
        insight = result["result"]
        sources = "\n".join(
            [f"- {doc.metadata.get('title', 'Unknown')} ({doc.metadata.get('url', '')})"
             for doc in result["source_documents"]]
        )
        return f"💰 **Price:** {price_info}\n\n📊 **Analysis:** {insight}\n\n📚 Sources:\n{sources}"

# === MAIN LOOP ===
print("💬 Ask about transcripts, prices, or both (type 'exit' to quit)\n")

while True:
    query = input("You: ").strip()
    if not query:
        print("⚠ Please type a question or 'exit' to quit.\n")
        continue
    if query.lower() in ["exit", "quit"]:
        print("👋 Goodbye!")
        break

    response = handle_query(query)
    print(f"\n🤖 Bot: {response}\n{'-'*50}\n")
