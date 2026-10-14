"""
Finance Engine — free market data + local LLM analysis.
No paid APIs required (yfinance + CoinGecko).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from core.ollama_client import OllamaClient

logger = logging.getLogger("sentinel.finance")


class FinanceEngine:
    def __init__(self, ollama: Optional[OllamaClient] = None):
        self.ollama = ollama or OllamaClient()

    def stock_quote(self, symbol: str) -> Dict[str, Any]:
        """Get stock/ETF quote via yfinance."""
        try:
            import yfinance as yf
            t = yf.Ticker(symbol.upper())
            info = t.info or {}
            hist = t.history(period="5d")
            last = float(hist["Close"].iloc[-1]) if not hist.empty else None
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
            change = ((last - prev) / prev * 100) if last and prev else None
            return {
                "symbol": symbol.upper(),
                "name": info.get("shortName") or info.get("longName") or symbol,
                "price": last,
                "change_pct": round(change, 2) if change is not None else None,
                "currency": info.get("currency", "USD"),
                "market_cap": info.get("marketCap"),
                "pe": info.get("trailingPE"),
                "sector": info.get("sector"),
                "summary": (info.get("longBusinessSummary") or "")[:400],
            }
        except Exception as e:
            logger.error(f"Stock quote failed: {e}")
            return {"error": str(e), "symbol": symbol}

    def crypto_quote(self, coin_id: str = "bitcoin") -> Dict[str, Any]:
        """CoinGecko free API."""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id.lower(),
                "vs_currencies": "usd,try",
                "include_24hr_change": "true",
                "include_market_cap": "true",
            }
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json().get(coin_id.lower(), {})
            return {
                "id": coin_id,
                "usd": data.get("usd"),
                "try": data.get("try"),
                "change_24h": data.get("usd_24h_change"),
                "market_cap_usd": data.get("usd_market_cap"),
            }
        except Exception as e:
            return {"error": str(e), "id": coin_id}

    def market_overview(self, symbols: Optional[List[str]] = None) -> str:
        symbols = symbols or ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA", "BTC-USD"]
        lines = [f"📊 Piyasa Özeti — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"]
        for s in symbols:
            if s.upper() in ("BTC", "BTC-USD", "BITCOIN"):
                q = self.crypto_quote("bitcoin")
                if "error" not in q:
                    ch = q.get("change_24h")
                    lines.append(f"BTC  ${q.get('usd'):,.0f}  ({ch:+.2f}% 24h)" if ch else f"BTC  ${q.get('usd')}")
            else:
                q = self.stock_quote(s)
                if "error" not in q and q.get("price"):
                    ch = q.get("change_pct")
                    lines.append(
                        f"{q['symbol']:6}  {q['price']:,.2f} {q.get('currency','')}  "
                        f"({ch:+.2f}%)" if ch is not None else f"{q['symbol']:6}  {q['price']}"
                    )
        return "\n".join(lines)

    def analyze(self, query: str) -> str:
        """Natural language finance question → data + LLM insight."""
        # Simple extraction
        lower = query.lower()
        data_parts = []

        # Detect crypto
        for coin, cid in [("bitcoin", "bitcoin"), ("btc", "bitcoin"), ("ethereum", "ethereum"), ("eth", "ethereum"), ("solana", "solana")]:
            if coin in lower:
                data_parts.append(str(self.crypto_quote(cid)))

        # Detect common tickers
        import re
        tickers = re.findall(r"\b([A-Z]{1,5})\b", query)
        for t in tickers[:5]:
            if t not in ("USD", "TRY", "API", "LLM", "AI"):
                data_parts.append(str(self.stock_quote(t)))

        if not data_parts:
            data_parts.append(self.market_overview())

        context = "\n".join(data_parts)
        prompt = f"""Aşağıdaki güncel piyasa verisine dayanarak kullanıcının sorusunu cevapla.
Kısa, net, rakamlı ol. Yatırım tavsiyesi verme, sadece analiz et.

Veri:
{context}

Soru: {query}

Cevap:"""
        try:
            return self.ollama.chat(prompt, system="Sen objektif bir finans analistisin. Sadece veriye dayalı konuş.")
        except Exception as e:
            return f"Veri:\n{context}\n\nAnaliz hatası: {e}"
