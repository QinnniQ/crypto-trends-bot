# src/frontend/streamlit_app.py
import os, time, requests, pandas as pd, altair as alt, plotly.express as px
import streamlit as st
from dotenv import load_dotenv

UI_BUILD = "v3.2"

# ---------- page / env ----------
st.set_page_config(page_title="Crypto Trends Bot", page_icon="🪙", layout="wide", initial_sidebar_state="collapsed")
load_dotenv()

DEFAULT_BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
VS_DEFAULT = os.getenv("VS_CURRENCY", "usd").lower()

CG_API_KEY = os.getenv("COINGECKO_API_KEY") or os.getenv("CG_API_KEY")
CG_HEADERS = {"accept": "application/json", "user-agent": "crypto-trends-bot/pro"}
if CG_API_KEY:
    CG_HEADERS["x-cg-demo-api-key"] = CG_API_KEY
    CG_HEADERS["x-cg-pro-api-key"] = CG_API_KEY

# ---------- styles ----------
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root{ --bg:#0b0f14; --bg2:#0f141c; --card:#111826; --muted:#9aa3af;
       --bd:#202635; --hi:#4F46E5; --good:#16a34a; --bad:#ef4444; --ink:#fff; --wrap:1180px; }
*{font-family:'Inter',system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
#MainMenu{display:none} header{visibility:hidden} footer{visibility:hidden}
[data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 800px at 8% 8%, var(--bg2) 0%, var(--bg) 55%, #070a10 100%);
}
.wrap { max-width: var(--wrap); margin: 0 auto; }
.topbar{ display:flex; align-items:center; justify-content:space-between; gap:16px;
  border:1px solid var(--bd); background:rgba(255,255,255,.03);
  border-radius:14px; padding:14px 16px; backdrop-filter: blur(8px); }
.brand{ display:flex; align-items:center; gap:12px; color:var(--ink) }
.brand .title{ font-weight:800; font-size:1.2rem; letter-spacing:.2px }
.pill{ display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px;
      border:1px solid var(--bd); background:rgba(255,255,255,.04); font-size:.9rem }
.dot{ width:8px; height:8px; border-radius:999px; background:#22c55e; }
.pill.bad .dot{ background:#ef4444 }
.section-title{ margin:18px 0 8px; font-weight:700; letter-spacing:.2px }
hr.line{ border:none; border-top:1px solid var(--bd); margin:18px 0 }
.card{ background: var(--card); border:1px solid var(--bd); border-radius:16px; padding:16px; box-shadow:0 8px 24px rgba(0,0,0,.25) }
.kpi .lbl{ color:var(--muted); font-weight:600; font-size:.92rem; }
.kpi .val{ font-size:1.9rem; font-weight:800; color:var(--ink); margin-top:6px }
.kpi .delta.up{ color: var(--good) } .kpi .delta.down{ color: var(--bad) }
.bubble{ padding:12px 14px; border-radius:14px; margin:6px 0; line-height:1.5; }
.bubble.user{ background:#1a1533; border:1px solid #2a2460; color:#e9e7ff; margin-left:auto; }
.bubble.bot{ background:#121826; border:1px solid var(--bd); color:#e7eaf1; }
.stButton > button{ background:linear-gradient(135deg,#4F46E5,#4338CA); color:#fff; border:0; padding:.6rem 1rem; border-radius:12px; font-weight:700; }
.stButton > button:hover{ filter:brightness(1.05) }
</style>
""", unsafe_allow_html=True)

# ---------- helpers ----------
def _get(url, params=None, tries=5, timeout=25, headers=None):
    headers = headers or {}; delay=0.7; last=None
    for _ in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200: return r.json()
            if r.status_code == 429:
                ra = r.headers.get("Retry-After"); time.sleep(int(ra) if (ra and ra.isdigit()) else delay)
            else:
                time.sleep(delay)
            delay = min(delay*2, 8); last=f"{r.status_code} {r.reason}"
        except Exception as e:
            last=str(e); time.sleep(delay); delay=min(delay*2, 8)
    raise RuntimeError(last or "GET failed")

def pct_class(x):
    try: return "up" if float(x or 0)>=0 else "down"
    except: return "up"

def health_ok():
    for p in ("/healthz","/health","/"):
        try:
            if requests.get(f"{BACKEND_URL}{p}", timeout=8).ok:
                return True
        except: pass
    return False

def ask_agent(q:str):
    url=f"{BACKEND_URL}/crypto-bot/invoke"
    variants=[{"input":q},{"input":{"question":q}},{"input":{"query":q}},{"input":{"input":q}},{"question":q}]
    last=None
    for payload in variants:
        try:
            r=requests.post(url,json=payload,timeout=60)
            if r.status_code==422: last=f"422 for {payload}"; continue
            r.raise_for_status(); data=r.json()
            if isinstance(data,dict):
                for k in("answer","output","result","content"):
                    if k in data: return str(data[k]),None
            return str(data),None
        except Exception as e:
            last=str(e)
    return None, f"Agent error: {last or 'unknown'}"

@st.cache_data(ttl=60)
def fetch_price(sym:str, vs:str):
    try:
        r=requests.get(f"{BACKEND_URL}/price/{sym}", params={"vs":vs}, timeout=20); r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"ok":False,"error":str(e)}

@st.cache_data(ttl=60)
def fetch_history(sym:str, days:int, vs:str):
    try:
        r=requests.get(f"{BACKEND_URL}/history/{sym}", params={"days":days,"vs":vs}, timeout=30); r.raise_for_status()
        data=r.json()
        if isinstance(data,dict) and data.get("ok") and isinstance(data.get("prices"),list):
            df=pd.DataFrame(data["prices"],columns=["ts_ms","price"]); df["time"]=pd.to_datetime(df["ts_ms"],unit="ms")
            return df[["time","price"]],None
        return None,"Unexpected /history payload"
    except Exception as e:
        return None,str(e)

@st.cache_data(ttl=600)
def fetch_top_coins(limit=24, vs="usd"):
    url="https://api.coingecko.com/api/v3/coins/markets"
    params={"vs_currency":vs,"order":"market_cap_desc","per_page":limit,"page":1,
            "price_change_percentage":"1h,24h,7d","sparkline":True}
    return pd.DataFrame(_get(url, params=params, headers=CG_HEADERS))

# ---------- runtime state (no sidebar) ----------
BACKEND_URL = st.session_state.get("BACKEND_URL", DEFAULT_BACKEND).rstrip("/")
VS = st.session_state.get("VS", VS_DEFAULT)

st.markdown('<div class="wrap">', unsafe_allow_html=True)
col1, col2 = st.columns([0.62, 0.38], gap="large")
with col1:
    st.markdown(f"""
    <div class="topbar">
      <div class="brand">
        <span style="font-size:1.2rem">🪙</span>
        <div class="title">Crypto Trends Bot <span style="opacity:.55;font-weight:600">({UI_BUILD})</span></div>
      </div>
      <div></div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    ok = health_ok()
    pill_cls = "" if ok else " bad"
    st.markdown(f"""
    <div class="topbar" style="justify-content:flex-end">
      <div class="pill{pill_cls}"><span class="dot"></span>{'Healthy' if ok else 'Not reachable'}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

with st.expander("⚙️ Settings", expanded=False):
    c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
    with c1:
        new_url = st.text_input("Backend URL", BACKEND_URL).rstrip("/")
    with c2:
        new_vs = st.selectbox("Quote", ["usd", "eur"], index=(0 if VS=="usd" else 1))
    with c3:
        live = st.toggle("Live 60s", value=False, help="Auto-refresh KPIs & heatmap")
    if new_url != BACKEND_URL or new_vs != VS:
        st.session_state["BACKEND_URL"] = new_url
        st.session_state["VS"] = new_vs
        st.rerun()

BACKEND_URL = st.session_state.get("BACKEND_URL", DEFAULT_BACKEND).rstrip("/")
VS = st.session_state.get("VS", VS_DEFAULT)

st.markdown('<hr class="line"/>', unsafe_allow_html=True)

# ---------- KPI row ----------
symbols = [("btc","BTC"), ("eth","ETH"), ("sol","SOL")]
cols = st.columns(3, gap="large")
for (sym, label), col in zip(symbols, cols):
    with col:
        p = fetch_price(sym, VS)
        if not p.get("ok"):
            st.markdown(f'<div class="card"><div class="kpi"><div class="lbl">{label}</div><div class="val">—</div><div class="lbl" style="margin-top:6px">{p.get("error","")}</div></div></div>', unsafe_allow_html=True)
            continue
        val_num = p.get(VS, p.get("price"))
        val = f"{val_num:,.2f}" if isinstance(val_num,(int,float)) else "—"
        d = p.get("change_24h", 0.0)
        delta = f"{d:+,.2f}%"
        st.markdown(f"""
        <div class="card kpi">
            <div class="lbl">{label} • <span class="delta {pct_class(d)}">{delta}</span></div>
            <div class="val">{val} {VS.upper()}</div>
        </div>
        """, unsafe_allow_html=True)

        df_hist, err = fetch_history(sym, days=7, vs=VS)
        if df_hist is not None and not df_hist.empty:
            ch = alt.Chart(df_hist).mark_line().encode(
                x=alt.X('time:T', axis=None),
                y=alt.Y('price:Q', axis=None)
            ).properties(height=58)
            st.altair_chart(ch, use_container_width=True)

st.markdown('<hr class="line"/>', unsafe_allow_html=True)

# ---------- Heatmap ----------
st.markdown('<div class="section-title">Market Heatmap</div>', unsafe_allow_html=True)
try:
    df = fetch_top_coins(limit=24, vs=VS)
    if not df.empty:
        df["label"] = df["symbol"].str.upper() + " $" + df["current_price"].round(2).astype(str)
        fig = px.treemap(
            df, path=[px.Constant("Market"), "label"], values="market_cap",
            color="price_change_percentage_24h",
            color_continuous_scale=["#ef4444","#fde047","#22c55e"],
            color_continuous_midpoint=0
        )
        fig.update_layout(margin=dict(t=0,l=0,r=0,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No market data yet.")
except Exception as e:
    st.warning(f"Heatmap paused (rate limit / network). {e}")

st.markdown('<hr class="line"/>', unsafe_allow_html=True)

# ---------- Chat ----------
st.markdown('<div class="section-title">Chat</div>', unsafe_allow_html=True)
if "chat" not in st.session_state: st.session_state.chat = []

c_chat, _ = st.columns([0.7, 0.3])
with c_chat:
    for msg in st.session_state.chat:
        cls = "user" if msg["role"]=="user" else "bot"
        st.markdown(f'<div class="bubble {cls}">{msg["content"]}</div>', unsafe_allow_html=True)

    default_q = st.session_state.get("prefill", "Compare ETH vs SOL narratives in the last 48 hours.")
    st.session_state["prefill"] = "What is the BTC price right now?"
    q = st.text_input("Ask the agent", value=default_q, placeholder="Short, specific questions work best")
    if st.button("Send", use_container_width=True):
        if q.strip():
            st.session_state.chat.append({"role":"user","content":q.strip()})
            with st.spinner("Thinking..."):
                ans, err = ask_agent(q.strip())
            st.session_state.chat.append({"role":"assistant","content":(f"⚠️ {err}" if err else ans or "(no answer)")})
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)  # close .wrap
