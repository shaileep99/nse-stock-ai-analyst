import streamlit as st
import pandas as pd
import os
import requests
import datetime
import urllib.request
from zipfile import ZipFile
import json

st.set_page_config(page_title="NSE Stock AI Analyst", page_icon="📈", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Space Mono', monospace; }
.stApp { background: #0d1117; color: #e6edf3; }
.metric-card {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 8px; padding: 16px 20px; margin-bottom: 8px;
}
.metric-card .label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
.metric-card .value { font-size: 24px; font-family: 'Space Mono', monospace; font-weight: 700; }
.up { color: #3fb950; } .down { color: #f85149; } .neutral { color: #e6edf3; }
.chat-user {
    background: #1f6feb; border-radius: 12px 12px 2px 12px;
    padding: 10px 16px; margin: 6px 0; max-width: 80%;
    margin-left: auto; font-size: 14px;
}
.summary-box {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 12px 12px 12px 2px;
    padding: 10px 16px; margin: 6px 0; font-size: 14px; line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)


# UDiFF column name mapping -> internal standard names
UDIFF_COL_MAP = {
    'TckrSymb': 'SYMBOL',
    'SctySrs': 'SERIES',
    'OpnPric': 'OPEN',
    'HghPric': 'HIGH',
    'LwPric': 'LOW',
    'ClsPric': 'CLOSE',
    'LastPric': 'LAST',
    'PrvsClsgPric': 'PREVCLOSE',
    'TtlTradgVol': 'TOTTRDQTY',
    'TtlTrfVal': 'TOTTRDVAL',
    'TradDt': 'TIMESTAMP',
    'TtlNbOfTxsExctd': 'TOTALTRADES',
    'ISIN': 'ISIN',
}

def normalize_columns(df):
    df.columns = df.columns.str.strip()
    # If it looks like UDiFF format, rename columns
    if 'TckrSymb' in df.columns:
        df = df.rename(columns=UDIFF_COL_MAP)
    # Ensure numeric types
    for col in ['OPEN','HIGH','LOW','CLOSE','PREVCLOSE','TOTTRDQTY','TOTTRDVAL','TOTALTRADES']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def download_bhavcopy(day, month, year):
    # New UDiFF URL format (post July 2024)
    date_str = f"{year}{str(month).zfill(2)}{str(day).zfill(2)}"
    # month here is already a number
    url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{date_str}_F_0000.csv.zip"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://www.nseindia.com/'
        })
        remote = urllib.request.urlopen(req, timeout=15)
        data = remote.read()
        remote.close()
        with open('File_Download.zip', 'wb') as f:
            f.write(data)
        with ZipFile('File_Download.zip', 'r') as z:
            names = z.namelist()
            z.extractall()
        os.remove('File_Download.zip')
        # Load and normalize
        csv_file = next((n for n in names if n.endswith('.csv')), None)
        if csv_file:
            df_new = pd.read_csv(csv_file)
            df_new = normalize_columns(df_new)
            if 'SERIES' in df_new.columns:
                df_new = df_new[df_new['SERIES'] == 'EQ']
            st.session_state.df = df_new
            return True, f"Downloaded {len(df_new):,} EQ records for {day}/{month}/{year}"
        return False, "CSV not found in zip"
    except Exception as e:
        return False, str(e)


def build_summary(df, symbol=None):
    if symbol:
        sub = df[df['SYMBOL'].str.upper() == symbol.upper()]
        if sub.empty:
            return f"No data found for symbol {symbol}."
        lines = [f"NSE stock data for {symbol} across {len(sub)} trading day(s):"]
        for _, row in sub.iterrows():
            chg = ((row['CLOSE'] - row['PREVCLOSE']) / row['PREVCLOSE'] * 100) if row['PREVCLOSE'] else 0
            lines.append(
                f"  Date: {row['TIMESTAMP']} | Open: {row['OPEN']} | High: {row['HIGH']} | "
                f"Low: {row['LOW']} | Close: {row['CLOSE']} | Prev Close: {row['PREVCLOSE']} | "
                f"Change: {chg:+.2f}% | Volume: {int(row['TOTTRDQTY']):,} | Trades: {int(row['TOTALTRADES']):,}"
            )
        return "\n".join(lines)
    else:
        top = df.nlargest(20, 'TOTTRDVAL')[['SYMBOL','OPEN','HIGH','LOW','CLOSE','PREVCLOSE','TOTTRDQTY','TOTTRDVAL','TIMESTAMP']].copy()
        top['CHG_PCT'] = ((top['CLOSE'] - top['PREVCLOSE']) / top['PREVCLOSE'] * 100).round(2)
        lines = [
            f"NSE Bhavcopy data - {df['TIMESTAMP'].nunique()} date(s), {df['SYMBOL'].nunique()} EQ stocks total.",
            "Top 20 stocks by traded value:"
        ]
        for _, row in top.iterrows():
            lines.append(
                f"  {row['SYMBOL']} ({row['TIMESTAMP']}): Close={row['CLOSE']}, Chg={row['CHG_PCT']:+.2f}%, "
                f"Vol={int(row['TOTTRDQTY']):,}, Val=Rs{row['TOTTRDVAL']/1e7:.2f}Cr"
            )
        gainers = df.copy()
        gainers['CHG_PCT'] = ((gainers['CLOSE'] - gainers['PREVCLOSE']) / gainers['PREVCLOSE'] * 100)
        top5g = gainers.nlargest(5, 'CHG_PCT')[['SYMBOL','CHG_PCT']]
        top5l = gainers.nsmallest(5, 'CHG_PCT')[['SYMBOL','CHG_PCT']]
        lines.append("Top 5 Gainers: " + ", ".join(f"{r.SYMBOL}({r['CHG_PCT']:+.1f}%)" for _, r in top5g.iterrows()))
        lines.append("Top 5 Losers: "  + ", ".join(f"{r.SYMBOL}({r['CHG_PCT']:+.1f}%)" for _, r in top5l.iterrows()))
        return "\n".join(lines)


def ask_groq(question, context):
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        return None, "Please enter your Groq API key in the sidebar."

    system = (
        "You are an expert NSE stock market analyst given bhavcopy data from the National Stock Exchange of India. "
        "Answer the user question using ONLY the data provided. "
        'Respond ONLY in this exact JSON format with no extra text or markdown: '
        '{"summary": "1-2 sentence answer", "table_title": "title", "table": [{"Col1": "val", "Col2": "val"}]} '
        "The table should have the most relevant rows. Use Rs prefix for prices. Use % suffix for change. "
        "If no table needed set table to []."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 1000,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Stock Data:\n{context}\n\nQuestion: {question}"}
        ]
    }
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload, timeout=30
        )
        if resp.status_code == 200:
            raw = resp.json()["choices"][0]["message"]["content"]
            clean = raw.strip().replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean)
            return parsed, None
        elif resp.status_code == 401:
            return None, "Invalid API key. Please check your Groq API key."
        else:
            return None, f"API error {resp.status_code}: {resp.text[:200]}"
    except json.JSONDecodeError:
        return {"summary": raw, "table": [], "table_title": ""}, None
    except Exception as e:
        return None, f"Request failed: {e}"


def render_answer(parsed):
    summary = parsed.get("summary", "")
    table = parsed.get("table", [])
    title = parsed.get("table_title", "")
    if summary:
        st.markdown(f'<div class="summary-box">{summary}</div>', unsafe_allow_html=True)
    if table:
        df_result = pd.DataFrame(table)
        if title:
            st.markdown(f"**{title}**")
        st.dataframe(df_result, use_container_width=True, hide_index=True)


# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

# Sidebar
with st.sidebar:
    st.markdown("## Settings")
    api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    if api_key:
        st.session_state["api_key"] = api_key

    st.markdown("---")
    st.markdown("### Load Data")
    mode = st.radio("Source", ["Upload CSV files", "Download today's bhavcopy"])

    if mode == "Upload CSV files":
        uploaded = st.file_uploader("Upload NSE bhavcopy CSV(s)", type="csv", accept_multiple_files=True)
        if uploaded:
            dfs = []
            for f in uploaded:
                df_tmp = pd.read_csv(f)
                df_tmp = normalize_columns(df_tmp)
                dfs.append(df_tmp)
            combined = pd.concat(dfs, ignore_index=True)
            if 'SERIES' in combined.columns:
                combined = combined[combined['SERIES'] == 'EQ']
            st.session_state.df = combined
            st.success(f"Loaded {len(combined):,} EQ records")
    else:
        if st.button("Download Today"):
            now = datetime.datetime.now()
            ok, msg = download_bhavcopy(now.day, now.month, now.year)
            st.success(msg) if ok else st.error(msg)

    st.markdown("---")
    st.markdown("### Sample Questions")
    samples = [
        "What are the top 5 gainers?",
        "What are the top 5 losers?",
        "Which stock had highest volume?",
        "Give me a market overview",
        "Show top 10 stocks by value",
    ]
    for s in samples:
        if st.button(s, key=s):
            st.session_state["prefill"] = s

# Main
st.markdown("# NSE Stock AI Analyst")
st.markdown("Ask anything about your NSE bhavcopy data in plain English.")

df = st.session_state.df

if not df.empty:
    df['CHG_PCT'] = ((df['CLOSE'] - df['PREVCLOSE']) / df['PREVCLOSE'].replace(0, float('nan')) * 100)
    gainers_count = (df['CHG_PCT'] > 0).sum()
    losers_count  = (df['CHG_PCT'] < 0).sum()
    top_gainer    = df.loc[df['CHG_PCT'].idxmax()]
    total_val     = df['TOTTRDVAL'].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="label">Total Stocks</div><div class="value neutral">{df["SYMBOL"].nunique()}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="label">Gainers</div><div class="value up">+{gainers_count}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="label">Losers</div><div class="value down">-{losers_count}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="label">Top Gainer</div><div class="value up">{top_gainer["SYMBOL"]} {top_gainer["CHG_PCT"]:+.1f}%</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="metric-card"><div class="label">Market Value</div><div class="value neutral">Rs {total_val/1e7:.0f} Cr</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    col_search, col_table = st.columns([1, 2])
    with col_search:
        symbol_input = st.text_input("Look up a symbol", placeholder="e.g. RELIANCE").upper()
        if symbol_input:
            sub = df[df['SYMBOL'] == symbol_input]
            if not sub.empty:
                for _, row in sub.iterrows():
                    chg = row['CHG_PCT']
                    color = "up" if chg > 0 else "down"
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="label">{row['SYMBOL']} - {row['TIMESTAMP']}</div>
                        <div class="value {color}">Rs {row['CLOSE']} <span style="font-size:14px">{chg:+.2f}%</span></div>
                        <div style="margin-top:8px;font-size:13px;color:#8b949e">
                            O: {row['OPEN']} &nbsp; H: {row['HIGH']} &nbsp; L: {row['LOW']}<br>
                            Vol: {int(row['TOTTRDQTY']):,} &nbsp; Trades: {int(row['TOTALTRADES']):,}
                        </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.warning(f"Symbol '{symbol_input}' not found.")

    with col_table:
        top10 = df.nlargest(10, 'TOTTRDVAL')[['SYMBOL','CLOSE','CHG_PCT','TOTTRDQTY','TOTALTRADES','TIMESTAMP']].copy()
        top10.columns = ['Symbol', 'Close Rs', 'Chg %', 'Volume', 'Trades', 'Date']
        top10['Chg %'] = top10['Chg %'].round(2)
        st.markdown("**Top 10 by Traded Value**")
        st.dataframe(top10, use_container_width=True, hide_index=True)

    st.markdown("---")

# Chat
st.markdown("### AI Chat")

if df.empty:
    st.info("Upload bhavcopy CSV files from the sidebar to get started.")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        render_answer(msg["content"])

prefill = st.session_state.pop("prefill", "")
question = st.chat_input("Ask about the stock data...")

if not question and prefill:
    question = prefill

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    st.markdown(f'<div class="chat-user">{question}</div>', unsafe_allow_html=True)

    if df.empty:
        parsed = {"summary": "No data loaded yet. Please upload bhavcopy CSV files from the sidebar first.", "table": []}
    else:
        words = question.upper().split()
        symbol_hit = next((w for w in words if w in df['SYMBOL'].values), None)
        context = build_summary(df, symbol_hit)
        with st.spinner("Analysing..."):
            parsed, error = ask_groq(question, context)
        if error:
            parsed = {"summary": f"Error: {error}", "table": []}

    st.session_state.messages.append({"role": "assistant", "content": parsed})
    render_answer(parsed)

if st.session_state.messages:
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()