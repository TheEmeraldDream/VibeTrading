"""
Portfolio reader — loads holdings from local/portfolio.json if present,
otherwise falls back to generic mock data for demo mode.
"""
import json
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)


class PortfolioReader:
    mode = "demo"
    connected = False

    def _local_portfolio(self) -> dict | None:
        path = Path(__file__).parent.parent / "local" / "portfolio.json"
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
        return None

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
                "mode":          "demo",
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

    # ------------------------------------------------------------------ #
    # Positions                                                            #
    # ------------------------------------------------------------------ #

    def get_positions(self) -> list[dict]:
        local = self._local_portfolio()
        if local and "positions" in local:
            result = []
            for p in local["positions"]:
                qty   = float(p["qty"])
                price = float(p["current_price"])
                entry = float(p["avg_entry_price"])
                result.append({
                    "symbol":          p["symbol"],
                    "qty":             qty,
                    "side":            "long",
                    "avg_entry_price": entry,
                    "current_price":   price,
                    "market_value":    round(price * qty, 2),
                    "unrealized_pl":   float(p["unrealized_pl"]),
                    "unrealized_plpc": float(p["unrealized_plpc"]),
                })
            return result
        mock = [
            ("AAPL", 15, 178.50, 184.20),
            ("NVDA", 5,  620.00, 645.80),
            ("MSFT", 8,  390.10, 385.50),
        ]
        result = []
        for sym, qty, entry, current in mock:
            current += random.uniform(-1, 1)
            pl  = (current - entry) * qty
            plpc = (current - entry) / entry * 100
            result.append({
                "symbol":          sym,
                "qty":             float(qty),
                "side":            "long",
                "avg_entry_price": entry,
                "current_price":   round(current, 2),
                "market_value":    round(current * qty, 2),
                "unrealized_pl":   round(pl, 2),
                "unrealized_plpc": round(plpc, 2),
            })
        return result
