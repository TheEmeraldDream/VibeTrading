"""
Portfolio reader — loads holdings from local/portfolio.json if present,
otherwise falls back to generic mock data for demo mode.

When a local portfolio is present, current prices are fetched live from
yfinance (via fetch_live_prices, called through run_in_executor in main.py)
so P&L is always calculated against real market prices.
"""
import json
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

_PORTFOLIO_TTL = 30   # seconds before re-reading the file from disk
_PRICE_TTL     = 60   # seconds before re-fetching live prices


class PortfolioReader:
    def __init__(self):
        self._portfolio_cache: dict | None = None
        self._portfolio_cache_time: float = 0
        self._price_cache: dict[str, float] = {}
        self._price_cache_time: float = 0
        self._portfolio_path = Path(__file__).parent.parent / "local" / "portfolio.json"
        self.mode = "local" if self._portfolio_path.exists() else "demo"

    # ------------------------------------------------------------------ #
    # Internal helpers                                                      #
    # ------------------------------------------------------------------ #

    def _local_portfolio(self) -> dict | None:
        now = time.monotonic()
        if self._portfolio_cache is not None and now - self._portfolio_cache_time < _PORTFOLIO_TTL:
            return self._portfolio_cache
        path = self._portfolio_path
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                self._portfolio_cache = data
                self._portfolio_cache_time = now
                return data
            except Exception:
                pass
        self._portfolio_cache = None
        return None

    def fetch_live_prices(self, symbols: list[str]) -> dict[str, float]:
        """
        Fetch current prices from yfinance for all symbols.
        Blocking — call via asyncio.get_running_loop().run_in_executor().
        Results are cached for _PRICE_TTL seconds.
        """
        now = time.monotonic()
        if self._price_cache and now - self._price_cache_time < _PRICE_TTL:
            return self._price_cache
        if not YFINANCE_AVAILABLE or not symbols:
            return self._price_cache
        prices = {}
        for sym in symbols:
            try:
                fi = yf.Ticker(sym).fast_info
                price = getattr(fi, "last_price", None) or getattr(fi, "regular_market_price", None)
                if price:
                    prices[sym] = float(price)
            except Exception as e:
                logger.warning(f"Live price fetch failed for {sym}: {e}")
        if prices:
            self._price_cache = prices
            self._price_cache_time = now
        return self._price_cache

    # ------------------------------------------------------------------ #
    # Account                                                              #
    # ------------------------------------------------------------------ #

    def get_account(self) -> dict:
        local = self._local_portfolio()
        if local and "account" in local:
            a = local["account"]
            return {
                "equity":        a.get("equity", 0),
                "cash":          a.get("cash", 0),
                "buying_power":  a.get("buying_power", 0),
                "daily_pnl":     a.get("daily_pnl", 0),
                "daily_pnl_pct": a.get("daily_pnl_pct", 0),
                "mode":          self.mode,
                "status":        "ACTIVE",
            }
        base = 100_000.0
        pnl = random.uniform(-500, 1500)
        return {
            "equity":        base + pnl,
            "cash":          72_340.50,
            "buying_power":  144_681.00,
            "daily_pnl":     pnl,
            "daily_pnl_pct": pnl / base * 100,
            "mode":          "demo",
            "status":        "ACTIVE",
        }

    def _position_dict(self, symbol: str, qty: float, entry: float, price: float) -> dict:
        pl   = (price - entry) * qty
        plpc = (price - entry) / entry * 100
        return {
            "symbol":          symbol,
            "qty":             qty,
            "side":            "long",
            "avg_entry_price": entry,
            "current_price":   round(price, 2),
            "market_value":    round(price * qty, 2),
            "unrealized_pl":   round(pl, 2),
            "unrealized_plpc": round(plpc, 2),
        }

    # ------------------------------------------------------------------ #
    # Positions                                                            #
    # ------------------------------------------------------------------ #

    def get_positions(self) -> list[dict]:
        local = self._local_portfolio()
        if local and "positions" in local:
            result = []
            for p in local["positions"]:
                qty   = float(p["qty"])
                entry = float(p["avg_entry_price"])
                # Use live price if cached, otherwise fall back to the file value
                price = self._price_cache.get(p["symbol"], float(p.get("current_price", entry)))
                result.append(self._position_dict(p["symbol"], qty, entry, price))
            return result

        mock = [
            ("AAPL", 15, 178.50, 184.20),
            ("NVDA", 5,  620.00, 645.80),
            ("MSFT", 8,  390.10, 385.50),
        ]
        return [
            self._position_dict(sym, float(qty), entry, current + random.uniform(-1, 1))
            for sym, qty, entry, current in mock
        ]

    # ------------------------------------------------------------------ #
    # P&L history (candlestick chart)                                      #
    # ------------------------------------------------------------------ #

    def get_pnl_history(self, days: int = 30) -> list[dict]:
        """
        Returns daily portfolio P&L OHLC for the past `days` trading days.
        Each entry: {time, open, high, low, close} where values are unrealized $ P&L.
        Requires yfinance for live data; falls back to deterministic mock data in demo mode.
        """
        local = self._local_portfolio()
        if local and "positions" in local and YFINANCE_AVAILABLE:
            return self._live_pnl_history(local["positions"], days)
        return self._demo_pnl_history(days)

    def _live_pnl_history(self, positions: list[dict], days: int) -> list[dict]:
        import yfinance as yf

        end   = datetime.now()
        start = end - timedelta(days=days + 14)  # buffer for weekends/holidays
        candles: dict[str, dict[str, float]] = {}

        for p in positions:
            sym   = p["symbol"]
            qty   = float(p["qty"])
            entry = float(p["avg_entry_price"])
            try:
                hist = yf.Ticker(sym).history(start=start, end=end, interval="1d")
                for ts, row in hist.iterrows():
                    date = ts.strftime("%Y-%m-%d")
                    if date not in candles:
                        candles[date] = {"open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0}
                    candles[date]["open"]  += (row["Open"]  - entry) * qty
                    candles[date]["high"]  += (row["High"]  - entry) * qty
                    candles[date]["low"]   += (row["Low"]   - entry) * qty
                    candles[date]["close"] += (row["Close"] - entry) * qty
            except Exception as e:
                logger.warning(f"P&L history fetch failed for {sym}: {e}")

        result = sorted(
            [{"time": d, "open": round(v["open"], 2), "high": round(v["high"], 2),
              "low": round(v["low"], 2), "close": round(v["close"], 2)}
             for d, v in candles.items()],
            key=lambda x: x["time"],
        )
        return result[-days:]

    def _demo_pnl_history(self, days: int) -> list[dict]:
        """Deterministic mock P&L history for demo mode."""
        rng = random.Random(42)
        today = datetime.now().date()

        # Collect the last `days` Mon–Fri dates in chronological order
        trading_days: list = []
        d = today
        while len(trading_days) < days:
            if d.weekday() < 5:
                trading_days.append(d)
            d -= timedelta(days=1)
        trading_days.reverse()

        result = []
        pnl = 0.0
        for d in trading_days:
            change = rng.gauss(15, 180)
            open_  = pnl
            close  = pnl + change
            high   = max(open_, close) + abs(rng.gauss(0, 70))
            low    = min(open_, close) - abs(rng.gauss(0, 70))
            result.append({
                "time":  d.strftime("%Y-%m-%d"),
                "open":  round(open_, 2),
                "high":  round(high, 2),
                "low":   round(low, 2),
                "close": round(close, 2),
            })
            pnl = close

        return result
