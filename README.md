# VibeTradingNews

A dark minimalist news aggregator for your stock holdings — powered by Claude AI.

Pulls recent financial news for every position in your portfolio, correlates it with price movements, and lets you ask Claude to explain what's actually driving your P&L.

---

## What it does

- **Holdings dashboard** — equity, cash, daily P&L, and all open positions displayed in the left panel.
- **News feed** — fetches recent financial news for your held symbols via Yahoo Finance. Refreshes automatically every 5 minutes.
- **Per-holding news filter** — click any holding in the left panel to filter the news feed to that symbol. Each holding shows how many articles are linked to it.
- **Claude news analyst** — hit **ANALYZE** for an automatic breakdown of which news events are likely driving price movements in your portfolio. Or ask anything in plain English.
- **Demo mode** — runs without any API keys using realistic mock data for both positions and news.

---

## Requirements

- Python 3.11+
- An [Anthropic](https://console.anthropic.com) API key for Claude

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/TheEmeraldDream/VibeTradingNews.git
cd VibeTradingNews
```

### 2. Configure your key

```bash
cp .env.example .env
```

```env
ANTHROPIC_API_KEY=sk-ant-...        # Powers Claude analysis
```

> **No key?** The app boots in **demo mode** automatically — mock positions and mock news, no credentials needed.

### 3. Launch

**Windows:**
```
run.bat
```

**Mac / Linux:**
```bash
chmod +x run.sh && ./run.sh
```

The script creates a virtual environment, installs dependencies, and opens your browser at `http://localhost:8000/app`.

---

## Manual startup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate      # Mac/Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## Using the dashboard

### Left panel — Account & Holdings
Shows equity, cash, buying power, and daily P&L at the top. Below that is a list of your open positions with current price, unrealized P&L, and a count of how many news articles are linked to each symbol. Clicking a holding filters the news feed.

### Center panel — News Feed
Displays recent news for your held symbols, sorted newest first. Use the filter chips at the top to narrow by symbol, or click **ALL** to see everything. Article headlines link out to the source when a URL is available. News refreshes automatically every 5 minutes — or hit **REFRESH NEWS** in the header to force it.

### Right panel — Claude News Analyst
Click **ANALYZE NEWS IMPACT** for an automatic analysis of how recent news may be affecting your holdings. Claude gets your full portfolio context (positions, prices, P&L) and the 25 most recent articles before responding.

You can also ask specific questions:
- `"Why did NVDA drop today?"`
- `"What's the biggest risk in my portfolio based on recent news?"`
- `"Summarize the AAPL news from this week"`
- `"Which of my holdings has the most negative news sentiment?"`

---

## Local portfolio

To use your real holdings locally without affecting the shipped version, create `local/portfolio.json` (this folder is gitignored):

```json
{
  "account": {
    "equity": 42242.65,
    "cash": 150.75,
    "buying_power": 150.75,
    "daily_pnl": 139.55,
    "daily_pnl_pct": 0.33
  },
  "positions": [
    {
      "symbol": "VTI",
      "qty": 10,
      "avg_entry_price": 200.00,
      "current_price": 215.00,
      "unrealized_pl": 150.00,
      "unrealized_plpc": 7.5
    }
  ]
}
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       Browser                                │
│                                                              │
│  ┌──────────────┐   ┌───────────────────┐   ┌────────────┐  │
│  │   Holdings   │◄─►│     News Feed     │   │   Claude   │  │
│  │  + Account   │   │ (filter by symbol)│   │  Analyst   │  │
│  └──────────────┘   └───────────────────┘   └─────┬──────┘  │
│         │                    ▲                     │ SSE     │
│      click                   │ WebSocket           │ stream  │
│      filters                 │ snapshot            │         │
└─────────┼────────────────────┼─────────────────────┼─────────┘
          │                    │                     │
┌─────────┼────────────────────┼─────────────────────┼─────────┐
│         │           Backend  │                     │         │
│         │                    │                     │         │
│  ┌──────┴──────┐   ┌─────────┴────────┐   ┌───────┴──────┐  │
│  │  Portfolio  │   │   News Service   │   │  AI Service  │  │
│  │   Reader   │   │  refresh every   │   │              │  │
│  │             │   │    5 minutes     │   │              │  │
│  └─────────────┘   └────────┬─────────┘   └──────┬───────┘  │
└───────────────────────────── ┼──────────────────── ┼──────────┘
                               │                     │
                       ┌───────┴──────┐    ┌─────────┴────┐
                       │    Yahoo     │    │  Anthropic   │
                       │   Finance    │    │  Claude API  │
                       └──────────────┘    └──────────────┘
```

**Data flows:**
1. On startup and every 5 minutes — backend reads positions, pulls news for held symbols, caches articles, and broadcasts a snapshot over WebSocket
2. Browser connects via WebSocket — receives account, positions, and news on connect and on each refresh
3. Clicking a holding — filters the news feed client-side with no additional request
4. Clicking ANALYZE or sending a message — backend builds context from live positions and cached news, streams Claude's response back as SSE

---

## Project structure

```
VibeTrading/
├── .env.example          # Key template — never commit the real .env
├── run.bat               # Windows launcher
├── run.sh                # Mac/Linux launcher
├── backend/
│   ├── main.py           # FastAPI app — REST, WebSocket, SSE, news refresh loop
│   ├── broker.py         # Portfolio reader (local/portfolio.json or mock fallback)
│   ├── news.py           # Yahoo Finance news with mock fallback
│   ├── claude_client.py  # Claude streaming integration for news analysis
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── local/                # Gitignored — personal portfolio data goes here
```

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/account` | Account balance and daily P&L |
| `GET` | `/api/positions` | Current positions |
| `GET` | `/api/news` | Cached news articles for current holdings |
| `POST` | `/api/news/refresh` | Force a news refresh and broadcast |
| `GET` | `/api/snapshot` | Account + positions + news in one call |
| `GET` | `/api/status` | App status, Claude availability, news info |
| `POST` | `/api/claude` | Stream Claude analysis (SSE) |
| `WS` | `/ws` | Live snapshot updates every 5 minutes |

---

## Security

- `.env` is gitignored — API keys stay local
- `local/` is gitignored — personal portfolio data stays local
- No brokerage connection — no orders can be placed
