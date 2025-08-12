import os
import requests
import gradio as gr
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA

# === LOAD ENV VARIABLES ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found in .env file.")

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
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": symbol.lower(), "vs_currencies": "usd", "include_24hr_change": "true"}
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
    q = query.lower()
    price_keywords = ["price", "current", "worth", "value", "update", "today", "latest"]
    analysis_keywords = ["say", "opinion", "think", "analysis", "view", "news", "report", "insight"]

    price_asked = any(word in q for word in price_keywords)
    analysis_asked = any(word in q for word in analysis_keywords)

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

# === HANDLE QUERY WITH STYLING & CLICKABLE LINKS ===
def handle_query(query: str):
    query_type = detect_query_type(query)
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

    def build_sources(source_docs):
        sources_html = ""
        for doc in source_docs:
            title = doc.metadata.get("title", "Unknown Source")
            url = doc.metadata.get("url", "")
            if url:
                sources_html += f"🔗 <a href='{url}' target='_blank'>{title}</a><br>"
            else:
                sources_html += f"📄 {title}<br>"
        return sources_html

    # Price only
    if query_type == "price":
        if coin_symbol:
            price_info = get_crypto_price(coin_symbol)
            return f"<div style='background-color:#d4edda; color:#155724; padding:10px; border-radius:8px;'><b>💰 {coin_symbol.upper()} Price:</b> {price_info}</div>"
        else:
            return "❌ Please specify a cryptocurrency for price lookup."

    # Analysis only
    if query_type == "analysis":
        result = qa.invoke({"query": query})
        answer = result["result"]
        sources_html = build_sources(result["source_documents"])
        return (
            f"<div style='background-color:#cce5ff; color:#004085; padding:10px; border-radius:8px;'><b>📊 Analysis:</b> {answer}</div>"
            f"<div style='background-color:#f8f9fa; color:#383d41; padding:10px; border-radius:8px; margin-top:5px;'><b>📚 Sources:</b><br>{sources_html}</div>"
        )

    # Hybrid: Price + Analysis
    if query_type == "hybrid":
        price_info = get_crypto_price(coin_symbol) if coin_symbol else "❌ No coin specified."
        result = qa.invoke({"query": query})
        insight = result["result"]
        sources_html = build_sources(result["source_documents"])
        return (
            f"<div style='background-color:#d4edda; color:#155724; padding:10px; border-radius:8px;'><b>💰 Price:</b> {price_info}</div>"
            f"<div style='background-color:#cce5ff; color:#004085; padding:10px; border-radius:8px; margin-top:5px;'><b>📊 Analysis:</b> {insight}</div>"
            f"<div style='background-color:#f8f9fa; color:#383d41; padding:10px; border-radius:8px; margin-top:5px;'><b>📚 Sources:</b><br>{sources_html}</div>"
        )

# === CHATBOT TEXT HANDLER ===
def chat_with_bot(message, history):
    if not message.strip():
        return history + [{"role": "assistant", "content": "⚠ Please enter a question."}]

    bot_response = handle_query(message)
    return history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": bot_response}
    ]

# === VOICE HANDLER ===
def handle_voice(file_path, history):
    if not file_path:
        return history

    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    query_text = result["text"]

    bot_reply = handle_query(query_text)
    return history + [
        {"role": "user", "content": f"(voice) {query_text}"},
        {"role": "assistant", "content": bot_reply}
    ]

# === BUILD GRADIO UI ===
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 💬 Crypto Trends Bot")
    gr.Markdown("Ask about **transcripts**, **live prices**, or **both**.\nSpeak or type your question.")

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="Conversation", type="messages")
            msg = gr.Textbox(label="Your Message", placeholder="e.g. Update me on ETH today", lines=1)
            voice = gr.Audio(sources=["microphone"], type="filepath", label="🎙 Speak your query")

            msg.submit(chat_with_bot, [msg, chatbot], chatbot)
            voice.change(handle_voice, [voice, chatbot], chatbot)

# === RUN APP ===
if __name__ == "__main__":
    demo.launch()
