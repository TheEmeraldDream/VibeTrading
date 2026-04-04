"""
News aggregator — fetches financial news for stock holdings via Alpaca.
Falls back to mock news in demo mode.
"""
import logging
import random
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

try:
    from alpaca.data.historical.news import NewsClient
    from alpaca.data.requests import NewsRequest
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False
    logger.warning("alpaca-py NewsClient not available — mock news only")


class NewsAggregator:
    def __init__(self, api_key: str, secret_key: str):
        self._demo = not (api_key and secret_key) or not NEWS_AVAILABLE
        self._client = None

        if not self._demo:
            try:
                self._client = NewsClient(api_key=api_key, secret_key=secret_key)
                logger.info("News client initialized")
            except Exception as e:
                logger.warning(f"News client init failed: {e}. Using mock news.")
                self._demo = True

    @property
    def demo(self) -> bool:
        return self._demo

    def get_news(self, symbols: list[str], limit: int = 40) -> list[dict]:
        if self._demo or not symbols:
            return self._mock_news(symbols)
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=7)
            req = NewsRequest(
                symbols=symbols,
                start=start,
                end=end,
                limit=limit,
            )
            response = self._client.get_news(req)
            articles = [self._fmt(a) for a in response.news]
            articles.sort(key=lambda a: a["published_at"], reverse=True)
            return articles
        except Exception as e:
            logger.error(f"get_news error: {e}")
            return self._mock_news(symbols)

    def _fmt(self, a) -> dict:
        return {
            "id": str(a.id),
            "headline": a.headline,
            "summary": a.summary or "",
            "author": a.author or "",
            "source": a.source or "",
            "url": a.url or "",
            "symbols": list(a.symbols or []),
            "published_at": a.created_at.isoformat() if a.created_at else "",
        }

    def _mock_news(self, symbols: list[str]) -> list[dict]:
        templates = [
            ("{sym} Q{q} earnings beat estimates; EPS ${eps:.2f} vs ${est:.2f} expected",
             "{sym} reported Q{q} earnings of ${eps:.2f} per share, topping analyst expectations of ${est:.2f}. Revenue also beat, driven by strong demand and margin expansion across key segments."),
            ("Analysts raise {sym} price target to ${pt} following strong guidance",
             "Multiple Wall Street firms raised their price targets on {sym} after the company issued upbeat forward guidance, citing robust demand, improving margins, and continued market share gains."),
            ("{sym} completes ${deal}B acquisition to expand into {market}",
             "{sym} closed its ${deal}B deal targeting the {market} space. Management called the acquisition immediately accretive and said it accelerates the company's long-term growth strategy."),
            ("{sym} under regulatory scrutiny over {topic}; shares slide",
             "Regulators announced an inquiry into {sym}'s {topic} practices. The company said it is cooperating fully and does not expect any material financial impact from the investigation."),
            ("{sym} COO departure announced; leadership transition underway",
             "{sym} confirmed its COO will step down at month-end. The board named an interim leader while conducting a permanent executive search. Some investors flagged concern over timing."),
            ("{sym} new product launch receives strong early demand signals",
             "{sym} unveiled its latest product lineup. Early reviews and pre-order data suggest demand is exceeding internal targets, according to sources with knowledge of supply chain projections."),
            ("{sym} cuts full-year outlook citing supply chain headwinds",
             "{sym} trimmed its full-year revenue guidance by 3-5%, pointing to supply chain disruptions. Management expects normalization by year-end but flagged ongoing risks to production timelines."),
            ("{sym} board extends buyback by $2B; dividend raised 8%",
             "The board of {sym} approved a $2B expansion of its share repurchase program and raised the quarterly dividend by 8%, signaling confidence in the company's near-term cash flow outlook."),
        ]
        markets = ["enterprise AI", "cloud infrastructure", "Southeast Asia", "clean energy"]
        topics = ["data privacy", "antitrust", "labor practices", "export compliance"]
        now = datetime.now(timezone.utc)
        articles = []
        idx = 0
        per = max(3, 20 // max(len(symbols), 1))
        for sym in symbols:
            rng = random.Random(sum(ord(c) for c in sym) + 7)
            for _ in range(per):
                th, ts = rng.choice(templates)
                hrs = rng.randint(1, 120)
                q = rng.randint(1, 4)
                eps = round(rng.uniform(1.5, 6.0), 2)
                est = round(eps - rng.uniform(0.05, 0.4), 2)
                pt = rng.randint(120, 700)
                deal = round(rng.uniform(0.5, 20), 1)
                market = rng.choice(markets)
                topic = rng.choice(topics)
                fmt = dict(sym=sym, q=q, eps=eps, est=est, pt=pt, deal=deal, market=market, topic=topic)
                articles.append({
                    "id": f"mock-{idx}",
                    "headline": th.format(**fmt),
                    "summary": ts.format(**fmt),
                    "author": rng.choice(["Reuters", "Bloomberg", "AP Finance", "MarketWatch"]),
                    "source": rng.choice(["Reuters", "Bloomberg", "Benzinga", "The Street", "MarketWatch"]),
                    "url": "",
                    "symbols": [sym],
                    "published_at": (now - timedelta(hours=hrs)).isoformat(),
                })
                idx += 1
        articles.sort(key=lambda a: a["published_at"], reverse=True)
        return articles
