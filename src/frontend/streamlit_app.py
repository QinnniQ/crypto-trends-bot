# src/frontend/streamlit_app.py
import os
import time
import requests
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import plotly.express as px
from dotenv import load_dotenv

# optional auto-refresh add-on
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except Exception:
    HAS_AUTOREFRESH = False

st.set_page_config(page_title="Crypto Trends Bot", page_icon="🪙", layout="wide")

load_dotenv()
DEFAULT_BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
VS = "usd"

CG_API_KEY = os.getenv("COINGECKO_API_KEY") or os.getenv("CG_API_KEY")
COINGECKO_HEADERS = {"accept": "application/json", "user-agent": "crypto-trends-bot/0.2"}
if CG_API_KEY:
    COINGECKO_HEADERS["x-cg-demo-api-key"] = CG_API_KEY
    COINGECKO_HEADERS["x-cg-pro-api-key"] = CG_API_KEY

with st.sidebar:
    st.header("Settings")
    BACKEND_URL = st.text_input("Backend URL", value=DEFAULT_BACKEND).rstrip("/")
    st.caption("Example: http://localhost:8000")
    st.link_button("Open API docs", f"{BACKEND_URL}/docs")
    st.link_button("Agent Playground", f"{BACKEND_URL}/crypto-bot/playground")

st.caption(f"Frontend → Backend at: {BACKEND_URL}")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
  background: radial-gradient(1200px 800px at 10% 10%, #10131a 0%, #0b0e14 40%, #0a0c11 100%);
}
h1, h2, h3, h4, h5, h6 { letter-spacing: .3px }
.kpi-card {
  background: rgba(255,255,255,0.06); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 16px;
}
.stat { font-size: 1.6rem; font-weight: 700; }
.sub { opacity:.8; font-size:.9rem; }
.chip {
  display:inline-block; padding:6px 10px; margin:4px 6px; border-radius:999px;
  background: rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.12);
  font-size:.9rem;
}
.up { color:#31d0aa; } .down { color:#ff6b6b; }
</style>
""", unsafe_allow_html=True)

def _get(url, params=None, tries=5, timeout=20, headers=None):
    headers = headers or {}
    delay = 0.7
    last_err = None
    for _ in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                ra = r.headers.get("Retry-After")
                sleep_sec = int(ra) if (ra and ra.isdigit()) else delay
                time.sleep(sleep_sec)
            else:
                time.sleep(delay)
            delay = min(delay * 2, 8)
            last_err = requests.HTTPError(f"{r.status_code} for {r.url}")
        except Exception as e:
            last_err = e
            time.sleep(delay)
            delay = min(delay * 2, 8)
    raise last_err or RuntimeError("GET failed")

@st.cache_data(ttl=300)
def fetch_top_coins(limit=25, vs="usd"):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": vs, "order": "market_cap_desc", "per_page": limit,
              "page": 1, "price_change_percentage": "1h,24h,7d", "sparkline": True}
    data = _get(url, params=params, headers=COINGECKO_HEADERS)
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def fetch_trending():
    data = _get("https://api.coingecko.com/api/v3/search/trending", headers=COINGECKO_HEADERS)
    coins = []
    for item in data.get("coins", []):
        c = item.get("item", {})
        coins.append({"name": c.get("name"), "symbol": c.get("symbol"), "id": c.get("id")})
    return coins

def pct_class(x: float) -> str:
    try:
        return "up" if float(x or 0) >= 0 else "down"
    except Exception:
        return "up"

def health_ok():
    for path in ("/healthz", "/health"):
        try:
            r = requests.get(f"{BACKEND_URL}{path}", timeout=5)
            if r.ok:
                return True
        except Exception:
            pass
    return False

def ask_agent(question: str):
    url = f"{BACKEND_URL}/crypto-bot/invoke"
    tries = [
        {"input": question},
        {"input": {"question": question}},
        {"input": {"query": question}},
        {"input": {"input": question}},
        {"question": question},
    ]
    last_err = None
    for payload in tries:
        try:
            r = requests.post(url, json=payload, timeout=60)
            if r.status_code == 422:
                last_err = f"422 for payload: {payload}"
                continue
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                for k in ("answer", "output", "result"):
                    if k in data:
                        return str(data[k]), None
            return str(data), None
        except Exception as e:
            last_err = str(e)
    return None, f"Agent error: {last_err or 'unknown error'}"

@st.cache_data(ttl=60)
def fetch_price(symbol: str):
    try:
        r = requests.get(f"{BACKEND_URL}/price/{symbol}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

@st.cache_data(ttl=60)
def fetch_history(symbol: str, days: int = 7, vs: str = "usd"):
    try:
        r = requests.get(f"{BACKEND_URL}/history/{symbol}", params={"days": days, "vs": vs}, timeout=20)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            if data.get("ok") and isinstance(data.get("prices"), list):
                rows = data["prices"]
                if not rows:
                    return None, "No history returned."
                df = pd.DataFrame(rows, columns=["ts_ms", "price"])
                df["time"] = pd.to_datetime(df["ts_ms"], unit="ms")
                return df[["time", "price"]], None
            if "timestamps" in data and "prices" in data:
                df = pd.DataFrame({"time": pd.to_datetime(data["timestamps"], unit="ms"),
                                   "price": data["prices"]})
                return df, None
        return None, "Unexpected /history payload."
    except Exception as e:
        return None, str(e)

col1, col2 = st.columns([0.75, 0.25])
with col1:
    st.markdown("# 🪙 Crypto Trends Bot")
    st.caption("Live market glance • RAG answers with sources • Ask via text or voice")
with col2:
    if HAS_AUTOREFRESH:
        live = st.toggle("Live updates", value=False, help="Update tiles/heatmap every 60s")
        if live:
            st_autorefresh(interval=60_000, key="auto")
    else:
        st.caption("Auto-refresh disabled (install: streamlit-autorefresh)")

ok = health_ok()
st.write("**Backend status:** " + ("✅ Healthy" if ok else "❌ Not reachable"))
if not ok:
    st.info("Start the backend:\n`uvicorn src.backend.server:app --reload --port 8000`")

st.divider()

df_top = None
cg_err = None
try:
    df_top = fetch_top_coins(limit=25, vs=VS)
except Exception as e:
    cg_err = str(e)

symbols = ["bitcoin", "ethereum", "solana"]
k1, k2, k3 = st.columns(3)
kpi_cols = [k1, k2, k3]

for i, cg_id in enumerate(symbols):
    with kpi_cols[i]:
        if df_top is None or df_top.empty:
            st.markdown(f"<div class='kpi-card'><div class='sub'>Loading {cg_id}…</div></div>", unsafe_allow_html=True)
            if cg_err:
                st.caption(f"Market data paused: {cg_err}")
            continue

        subdf = df_top[df_top["id"] == cg_id]
        if subdf.empty:
            st.markdown(f"<div class='kpi-card'><div class='sub'>No data for {cg_id}</div></div>", unsafe_allow_html=True)
            continue

        row = subdf.iloc[0]
        sym = row["symbol"].upper()
        price = row["current_price"]
        ch24 = row.get("price_change_percentage_24h") or 0.0
        cls = pct_class(ch24)

        st.markdown(f"""
        <div class='kpi-card'>
          <div class='sub'>{sym} • 24h <span class='{cls}'>{ch24:+.2f}%</span></div>
          <div class='stat'>${price:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

        df_hist, err = fetch_history(row["symbol"], days=7, vs=VS)
        if err or df_hist is None:
            sp = row.get("sparkline_in_7d", {}).get("price", [])
            df_hist = pd.DataFrame({
                "time": pd.date_range(end=pd.Timestamp.utcnow(), periods=len(sp), freq="H"),
                "price": sp
            })

        if not df_hist.empty:
            line = alt.Chart(df_hist).mark_line().encode(
                x=alt.X('time:T', axis=None),
                y=alt.Y('price:Q', axis=None)
            ).properties(height=60)
            st.altair_chart(line, use_container_width=True)

st.divider()

st.subheader("Market Heatmap")
if df_top is None:
    st.warning("Hit CoinGecko rate limit. Try again in a minute, enable fewer updates, or add a COINGECKO_API_KEY.")
else:
    if not df_top.empty:
        df = df_top.copy()
        df["label"] = df["symbol"].str.upper() + "  $" + df["current_price"].round(2).astype(str)
        fig = px.treemap(
            df, path=[px.Constant("Market"), "label"],
            values="market_cap",
            color="price_change_percentage_24h",
            color_continuous_scale=["#ff6b6b", "#ffd166", "#31d0aa"],
            color_continuous_midpoint=0
        )
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No market data loaded yet.")

st.subheader("Trending")
try:
    tr = fetch_trending()
except Exception as e:
    tr = []
    st.caption(f"Trending paused: {e}")

if tr:
    chip_cols = st.columns(5)
    for idx, c in enumerate(tr):
        text = f"{c['symbol'].upper()} · {c['name']}"
        with chip_cols[idx % 5]:
            if st.button(text, key=f"chip-{c['id']}"):
                st.session_state["pre_filled"] = f"Tell me what's moving {c['symbol'].upper()} today."
    st.caption("Click a chip to pre-fill the agent prompt.")
else:
    st.write("No trending list right now.")

st.divider()

st.subheader("Ask the agent")
preset = st.session_state.get("pre_filled", "What is the BTC price right now?")
q = st.text_input("Your question", value=preset, placeholder="e.g., Summarize today’s BTC + SOL sentiment and show sources")

if st.button("Run", type="primary"):
    if not q.strip():
        st.warning("Type a question first.")
    else:
        with st.spinner("Thinking..."):
            answer, err = ask_agent(q.strip())
            if err:
                st.error(err)
            else:
                st.markdown("### Answer")
                st.write(answer)

st.divider()
st.subheader("🧠 Narrative mode")

colA, colB = st.columns([0.5, 0.5])
with colA:
    ticker = st.selectbox("Ticker", ["BTC", "ETH", "SOL", "AVAX", "ADA"], index=0)
with colB:
    hours = st.slider("Lookback window (hours)", min_value=12, max_value=168, value=48, step=12)

if st.button("Find top narratives"):
    prompt = (
        f"Summarize the top 3 narratives for {ticker} over the last {hours} hours. "
        f"Use transcripts, articles, and summaries in the vector store. "
        f"Include short bullet points and list sources with titles + URLs."
    )
    with st.spinner("Mining narratives..."):
        answer, err = ask_agent(prompt)
        if err:
            st.error(err)
        else:
            st.markdown("### Narratives")
            st.write(answer)

try:
    from audio_recorder_streamlit import audio_recorder
    st.subheader("🎙️ Voice ask (beta)")

    audio_bytes = audio_recorder(text="Record a question")
    lang = st.selectbox("Language", ["auto", "en", "es", "fr", "de", "it"], index=0)

    if audio_bytes and st.button("Transcribe & Ask"):
        files = {"file": ("voice.wav", audio_bytes, "audio/wav")}
        data = {} if lang == "auto" else {"language": lang}

        def show_http_error(prefix, err: requests.HTTPError):
            detail = ""
            try:
                detail = err.response.text
            except Exception:
                pass
            st.error(f"{prefix}: {err}\n{detail}")

        try:
            r = requests.post(f"{BACKEND_URL}/voice-ask", files=files, data=data, timeout=120)
            if r.status_code in (404, 405):
                raise RuntimeError(f"/voice-ask not available ({r.status_code})")
            r.raise_for_status()
            js = r.json()
            if not js.get("ok"):
                raise RuntimeError(js)

            st.write(f"**You said:** {js.get('question','')}")
            st.markdown("### Answer")
            st.write(js.get("answer","(no answer)"))

        except requests.HTTPError as e:
            show_http_error("Voice ask failed", e)

        except Exception:
            try:
                t = requests.post(f"{BACKEND_URL}/transcribe", files=files, data=data, timeout=120)
                t.raise_for_status()
                text = t.json().get("text", "").strip()
                if not text:
                    st.error("No text returned from transcription.")
                else:
                    st.write(f"**You said:** {text}")
                    with st.spinner("Asking the agent..."):
                        answer, err = ask_agent(text)
                        if err:
                            st.error(err)
                        else:
                            st.markdown("### Answer")
                            st.write(answer)
            except requests.HTTPError as e2:
                show_http_error("Transcription failed", e2)
            except Exception as e2:
                st.error(f"Voice flow failed: {e2}")
except Exception:
    st.caption("Install voice input: `pip install audio-recorder-streamlit`")
