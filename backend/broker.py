"""
Broker connector — read-only Alpaca wrapper with mock fallback for demo mode.
Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env to connect live/paper.
"""
import json
import os
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from alpaca.trading.client import TradingClient
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    logger.warning("alpaca-py not installed — running in demo mode")


class BrokerClient:
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY", "")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self.paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
        self.connected = False
        self.mode = "demo"
        self._client = None
        self._data_client = None

        if ALPACA_AVAILABLE and self.api_key and self.secret_key:
            try:
                self._client = TradingClient(
                    self.api_key, self.secret_key, paper=self.paper
                )
                self._data_client = StockHistoricalDataClient(
                    self.api_key, self.secret_key
                )
                self._client.get_account()
                self.connected = True
                self.mode = "paper" if self.paper else "live"
                logger.info(f"Broker connected — mode: {self.mode}")
            except Exception as e:
                logger.warning(f"Broker connection failed: {e}. Using demo mode.")

    # ------------------------------------------------------------------ #
    # Account                                                              #
    # ------------------------------------------------------------------ #

    def get_account(self) -> dict:
        if not self.connected:
            return self._mock_account()
        try:
            a = self._client.get_account()
            equity = float(a.equity)
            last_equity = float(a.last_equity)
            daily_pnl = equity - last_equity
            return {
                "equity": equity,
                "cash": float(a.cash),
                "buying_power": float(a.buying_power),
                "daily_pnl": daily_pnl,
                "daily_pnl_pct": (daily_pnl / last_equity * 100) if last_equity else 0,
                "mode": self.mode,
                "status": str(a.status),
            }
        except Exception as e:
            logger.error(f"get_account error: {e}")
            return self._mock_account()

    def _local_portfolio(self) -> dict | None:
        path = Path(__file__).parent.parent / "local" / "portfolio.json"
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _mock_account(self) -> dict:
        local = self._local_portfolio()
        if local and "account" in local:
            a = local["account"]
            return {
                "equity":        a.get("equity", 0),
                "cash":          a.get("cash", 0),
                "buying_power":  a.get("buying_power", 0),
                "daily_pnl":     a.get("daily_pnl", 0),
                "daily_pnl_pct": a.get("daily_pnl_pct", 0),
                "mode":          "demo",
                "status":        "ACTIVE",
            }
        base = 100_000.0
        pnl = random.uniform(-500, 1500)
        return {
            "equity": base + pnl,
            "cash": 72_340.50,
            "buying_power": 144_681.00,
            "daily_pnl": pnl,
            "daily_pnl_pct": pnl / base * 100,
            "mode": "demo",
            "status": "ACTIVE",
        }

    # ------------------------------------------------------------------ #
    # Positions                                                            #
    # ------------------------------------------------------------------ #

    def get_positions(self) -> list[dict]:
        if not self.connected:
            return self._mock_positions()
        try:
            positions = self._client.get_all_positions()
            return [
                {
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "side": "long" if float(p.qty) > 0 else "short",
                    "avg_entry_price": float(p.avg_entry_price),
                    "current_price": float(p.current_price),
                    "market_value": float(p.market_value),
                    "unrealized_pl": float(p.unrealized_pl),
                    "unrealized_plpc": float(p.unrealized_plpc) * 100,
                }
                for p in positions
            ]
        except Exception as e:
            logger.error(f"get_positions error: {e}")
            return self._mock_positions()

    def _mock_positions(self) -> list[dict]:
        local = self._local_portfolio()
        if local and "positions" in local:
            result = []
            for p in local["positions"]:
                qty     = float(p["qty"])
                price   = float(p["current_price"])
                entry   = float(p["avg_entry_price"])
                result.append({
                    "symbol":           p["symbol"],
                    "qty":              qty,
                    "side":             "long",
                    "avg_entry_price":  entry,
                    "current_price":    price,
                    "market_value":     round(price * qty, 2),
                    "unrealized_pl":    float(p["unrealized_pl"]),
                    "unrealized_plpc":  float(p["unrealized_plpc"]),
                })
            return result
        mock = [
            ("AAPL", 15, 178.50, 184.20),
            ("NVDA", 5, 620.00, 645.80),
            ("MSFT", 8, 390.10, 385.50),
        ]
        result = []
        for sym, qty, entry, current in mock:
            current += random.uniform(-1, 1)
            pl = (current - entry) * qty
            plpc = (current - entry) / entry * 100
            result.append({
                "symbol": sym,
                "qty": float(qty),
                "side": "long",
                "avg_entry_price": entry,
                "current_price": round(current, 2),
                "market_value": round(current * qty, 2),
                "unrealized_pl": round(pl, 2),
                "unrealized_plpc": round(plpc, 2),
            })
        return result

    # ------------------------------------------------------------------ #
    # Historical bars                                                      #
    # ------------------------------------------------------------------ #

    def get_bars(self, symbol: str, limit: int = 50) -> list[dict]:
        if not self.connected or self._data_client is None:
            return self._mock_bars(symbol, limit)
        try:
            end = datetime.utcnow()
            start = end - timedelta(days=limit * 2)
            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
                limit=limit,
            )
            bars = self._data_client.get_stock_bars(req)
            df = bars.df
            if df.empty:
                return self._mock_bars(symbol, limit)
            return [
                {
                    "t": str(row.Index[1]) if hasattr(row.Index, "__len__") else str(row.Index),
                    "o": float(row.open),
                    "h": float(row.high),
                    "l": float(row.low),
                    "c": float(row.close),
                    "v": float(row.volume),
                }
                for row in df.itertuples()
            ]
        except Exception as e:
            logger.error(f"get_bars error for {symbol}: {e}")
            return self._mock_bars(symbol, limit)

    def _mock_bars(self, symbol: str, limit: int = 50) -> list[dict]:
        seed = sum(ord(c) for c in symbol)
        random.seed(seed)
        price = 100.0 + (seed % 400)
        bars = []
        now = datetime.utcnow()
        for i in range(limit):
            price += random.uniform(-3, 3)
            bars.append({
                "t": (now - timedelta(days=limit - i)).isoformat(),
                "o": round(price - random.uniform(0, 1), 2),
                "h": round(price + random.uniform(0, 2), 2),
                "l": round(price - random.uniform(0, 2), 2),
                "c": round(price, 2),
                "v": random.randint(500_000, 5_000_000),
            })
        random.seed()
        return bars
