# NSE Stock AI Analyst 📈

An AI-powered stock market analysis app built with Python and Streamlit. Upload daily NSE bhavcopy data and query it in plain English — no SQL, no code.

Built for my father, a non-technical investor who wanted a simple way to explore market trends.

---

## Features

- **AI Chat Interface** — Ask questions like *"What are the top 5 losers?"* or *"Summarize RELIANCE"* and get structured table responses powered by Groq (LLaMA 3.3 70B)
- **Auto Download** — Fetches today's bhavcopy directly from NSE archives (UDiFF format)
- **Live Dashboard** — Gainers/losers count, top gainer, total market value at a glance
- **Symbol Lookup** — Instant OHLC + % change for any stock
- **Top 10 Table** — Ranked by traded value across all loaded files

---

## Tech Stack

- **Python** — ETL pipeline, data processing
- **Pandas** — Time-series data analysis
- **Streamlit** — Interactive web UI
- **Groq API** (LLaMA 3.3 70B) — Natural language querying
- **NSE UDiFF Bhavcopy** — Live equity market data

---

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/shaileep99/nse-stock-ai-analyst.git
cd nse-stock-ai-analyst
```

### 2. Install dependencies
```bash
pip install streamlit pandas requests
```

### 3. Get a free Groq API key
Sign up at [console.groq.com](https://console.groq.com) — it's free.

### 4. Run the app
```bash
streamlit run stock_ai_app.py
```

### 5. Use it
- Paste your Groq API key in the sidebar
- Upload NSE bhavcopy CSV files **or** click **Download Today** to fetch live data
- Ask anything in the chat box

---

## Example Questions

- *"What are the top 5 gainers today?"*
- *"Which stock had the highest trading volume?"*
- *"Give me a market overview"*
- *"Summarize INFY"*
- *"Show top 10 stocks by value"*

---

## Data Source

Daily bhavcopy data from [NSE India](https://www.nseindia.com/all-reports) — Capital Market UDiFF format (post July 2024).

---

## Author

**Shailee Patel** — [github.com/shaileep99](https://github.com/shaileep99)
