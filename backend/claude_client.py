"""
Claude API integration — streams financial news analysis.
Uses claude-opus-4-6 with adaptive thinking.
"""
import logging
import os
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a financial news analyst. The user holds a portfolio of stocks and wants to understand how recent news affects their positions.

Your job:
1. Identify which news articles are most likely driving price movements in the user's holdings
2. Explain the causal chain — why would this specific news move the price?
3. Distinguish sentiment-driven short-term moves from fundamental changes
4. Flag material risks or opportunities based on the news
5. Be specific: reference article headlines and their timing when drawing correlations

Keep responses concise and actionable. Lead with the most impactful observations for the user's actual holdings."""


class ClaudeClient:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._client = None

        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set — Claude assistant disabled")
            return

        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            logger.info("Claude client initialized (claude-opus-4-6)")
        except ImportError:
            logger.warning("anthropic package not installed")

    @property
    def available(self) -> bool:
        return self._client is not None

    def build_context(
        self,
        account: dict,
        positions: list[dict],
        news: list[dict],
    ) -> str:
        pos_lines = "\n".join(
            f"  {p['symbol']}: {p['qty']:.0f} shares @ ${p['avg_entry_price']:.2f} entry, "
            f"current ${p['current_price']:.2f} "
            f"(P&L: {p['unrealized_pl']:+.2f}, {p['unrealized_plpc']:+.2f}%)"
            for p in positions
        ) or "  (none)"

        news_lines = []
        for a in news[:25]:
            pub = a.get("published_at", "")[:16].replace("T", " ")
            syms = ", ".join(a.get("symbols", []))
            summary = a.get("summary", "")[:200]
            news_lines.append(
                f"[{pub}] {syms} · {a.get('source', '')}\n"
                f"  {a.get('headline', '')}\n"
                f"  {summary}"
            )

        news_block = "\n\n".join(news_lines) if news_lines else "  (no recent news)"

        return f"""--- PORTFOLIO CONTEXT ---

ACCOUNT (mode: {account.get('mode', 'unknown')}):
  Equity:    ${account.get('equity', 0):,.2f}
  Daily P&L: {account.get('daily_pnl', 0):+,.2f} ({account.get('daily_pnl_pct', 0):+.2f}%)

HOLDINGS:
{pos_lines}

RECENT NEWS (last 7 days, newest first):
{news_block}

--- END CONTEXT ---"""

    async def stream_response(
        self,
        user_prompt: str,
        context: str,
    ) -> AsyncGenerator[str, None]:
        if not self.available:
            yield "Claude is not available. Please set ANTHROPIC_API_KEY in your .env file."
            return

        full_message = f"{context}\n\nUser request: {user_prompt}"

        try:
            async with self._client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=4096,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": full_message}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Claude stream error: {e}")
            yield f"\n\n[Error communicating with Claude: {e}]"
