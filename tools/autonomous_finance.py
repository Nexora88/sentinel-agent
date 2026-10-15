"""
Sentinel Autonomous Finance — Paper Trading Engine

DEFAULT: Simulation only (no real money).
Hard constraints that the LLM cannot override:
- Max 5% of portfolio per trade
- Automatic stop-loss / take-profit levels
- Daily loss circuit breaker
- No real exchange orders unless REAL_TRADING_ENABLED=true AND explicit keys

This module is intentionally conservative.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from core.ollama_client import OllamaClient

logger = logging.getLogger("sentinel.autonomous_finance")

# === HARD CONSTRAINTS (code-level, not LLM-overridable) ===
MAX_POSITION_PCT = 0.05          # max 5% of equity per trade
DEFAULT_STOP_LOSS_PCT = 0.02     # 2%
DEFAULT_TAKE_PROFIT_PCT = 0.06   # 6%
DAILY_LOSS_LIMIT_PCT = 0.03      # 3% daily loss → circuit breaker 24h
MIN_TRADE_USD = 1.0
MAX_OPEN_POSITIONS = 5


class AutonomousFinance:
    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        state_dir: str = "./memory/finance",
        starting_balance: float = 1000.0,
    ):
        self.ollama = ollama or OllamaClient()
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / "portfolio.json"
        self.log_path = self.state_dir / "thought_log.jsonl"

        self.real_trading = os.getenv("REAL_TRADING_ENABLED", "false").lower() == "true"
        self.starting_balance = starting_balance
        self.state = self._load_state()

    # ---------- persistence ----------
    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError(
                    f"Paper portfolio is unreadable; preserve and recover {self.state_path} before restarting."
                ) from exc
        return {
            "mode": "paper",
            "cash_usd": self.starting_balance,
            "equity_start": self.starting_balance,
            "positions": {},          # symbol -> {qty, entry, stop, take, opened_at}
            "closed_trades": [],
            "daily_pnl": 0.0,
            "daily_pnl_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "circuit_breaker_until": None,
            "total_trades": 0,
            "winning_trades": 0,
        }

    def _save_state(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=str(self.state_dir),
                prefix=".portfolio-", suffix=".tmp", delete=False
            ) as temp:
                json.dump(self.state, temp, ensure_ascii=False, indent=2)
                temp.flush()
                os.fsync(temp.fileno())
                temp_name = temp.name
            try:
                os.chmod(temp_name, 0o600)
            except OSError:
                pass
            os.replace(temp_name, self.state_path)
            try:
                os.chmod(self.state_path, 0o600)
            except OSError:
                pass
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

    def _log_thought(self, thought: str, action: str = "info", meta: Optional[dict] = None) -> None:
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "action": action,
            "thought": thought,
            "meta": meta or {},
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ---------- market data (free) ----------
    def get_price(self, symbol: str) -> Optional[float]:
        """Fetch external prices only after an explicit privacy opt-in."""
        if os.getenv("ALLOW_EXTERNAL_FINANCE_DATA", "false").lower() != "true":
            return None
        # Map common symbols
        id_map = {
            "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
            "BNB": "binancecoin", "XRP": "ripple", "ADA": "cardano",
            "DOGE": "dogecoin", "AVAX": "avalanche-2", "DOT": "polkadot",
            "LINK": "chainlink", "MATIC": "matic-network", "NEAR": "near",
        }
        coin_id = id_map.get(symbol.upper().replace("USDT", ""), symbol.lower())
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            return float(data[coin_id]["usd"])
        except Exception as e:
            logger.warning(f"Price fetch failed for {symbol}: {e}")
            return None

    def get_market_overview(self) -> str:
        symbols = ["BTC", "ETH", "SOL", "BNB", "XRP"]
        lines = []
        for s in symbols:
            p = self.get_price(s)
            if p:
                lines.append(f"{s}: ${p:,.2f}")
        return " | ".join(lines) if lines else "Fiyat verisi alınamadı"

    # ---------- risk engine (hard constraints) ----------
    def _reset_daily_if_needed(self) -> None:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.state.get("daily_pnl_date") != today:
            self.state["daily_pnl"] = 0.0
            self.state["daily_pnl_date"] = today

    def _circuit_breaker_active(self) -> bool:
        until = self.state.get("circuit_breaker_until")
        if not until:
            return False
        if datetime.utcnow() < datetime.fromisoformat(until):
            return True
        self.state["circuit_breaker_until"] = None
        self._save_state()
        return False

    def _trigger_circuit_breaker(self, reason: str) -> None:
        until = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        self.state["circuit_breaker_until"] = until
        self._save_state()
        self._log_thought(f"CIRCUIT BREAKER: {reason}. Trading paused 24h.", "circuit_breaker")

    def equity(self) -> float:
        """Cash + mark-to-market positions."""
        total = float(self.state["cash_usd"])
        for sym, pos in self.state["positions"].items():
            price = self.get_price(sym) or pos["entry"]
            total += pos["qty"] * price
        return total

    def _max_position_usd(self) -> float:
        return self.equity() * MAX_POSITION_PCT

    # ---------- paper trading actions ----------
    def open_long(self, symbol: str, reasoning: str) -> Dict[str, Any]:
        symbol = symbol.upper().replace("USDT", "")
        self._reset_daily_if_needed()

        if self._circuit_breaker_active():
            msg = "Devre kesici aktif — 24 saat işlem yok."
            self._log_thought(msg, "blocked")
            return {"success": False, "error": msg}

        if len(self.state["positions"]) >= MAX_OPEN_POSITIONS:
            return {"success": False, "error": f"Max açık pozisyon: {MAX_OPEN_POSITIONS}"}

        if symbol in self.state["positions"]:
            return {"success": False, "error": f"{symbol} zaten açık"}

        price = self.get_price(symbol)
        if not price or price <= 0:
            return {"success": False, "error": f"Fiyat alınamadı: {symbol}"}

        max_usd = self._max_position_usd()
        cash = float(self.state["cash_usd"])
        trade_usd = min(max_usd, cash * 0.95)  # leave a little cash
        if trade_usd < MIN_TRADE_USD:
            return {"success": False, "error": "Yetersiz bakiye"}

        qty = trade_usd / price
        stop = price * (1 - DEFAULT_STOP_LOSS_PCT)
        take = price * (1 + DEFAULT_TAKE_PROFIT_PCT)

        self.state["cash_usd"] = cash - trade_usd
        self.state["positions"][symbol] = {
            "qty": qty,
            "entry": price,
            "stop": stop,
            "take": take,
            "opened_at": datetime.utcnow().isoformat(),
            "reasoning": reasoning[:500],
        }
        self.state["total_trades"] = self.state.get("total_trades", 0) + 1
        self._save_state()

        thought = (
            f"LONG {symbol} @ ${price:.4f} | size=${trade_usd:.2f} ({MAX_POSITION_PCT*100:.0f}% rule) | "
            f"SL=${stop:.4f} TP=${take:.4f} | {reasoning[:200]}"
        )
        self._log_thought(thought, "open_long", {"symbol": symbol, "price": price, "usd": trade_usd})

        return {
            "success": True,
            "mode": "paper",
            "symbol": symbol,
            "side": "long",
            "price": price,
            "qty": qty,
            "usd": trade_usd,
            "stop_loss": stop,
            "take_profit": take,
            "reasoning": reasoning,
        }

    def close_position(self, symbol: str, reason: str = "manual") -> Dict[str, Any]:
        symbol = symbol.upper().replace("USDT", "")
        pos = self.state["positions"].get(symbol)
        if not pos:
            return {"success": False, "error": f"Açık pozisyon yok: {symbol}"}

        price = self.get_price(symbol) or pos["entry"]
        pnl = (price - pos["entry"]) * pos["qty"]
        pnl_pct = (price - pos["entry"]) / pos["entry"]

        self.state["cash_usd"] = float(self.state["cash_usd"]) + pos["qty"] * price
        del self.state["positions"][symbol]

        self._reset_daily_if_needed()
        self.state["daily_pnl"] = float(self.state.get("daily_pnl", 0)) + pnl
        if pnl > 0:
            self.state["winning_trades"] = self.state.get("winning_trades", 0) + 1

        trade_record = {
            "symbol": symbol,
            "entry": pos["entry"],
            "exit": price,
            "qty": pos["qty"],
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "reason": reason,
            "closed_at": datetime.utcnow().isoformat(),
        }
        self.state.setdefault("closed_trades", []).append(trade_record)
        self.state["closed_trades"] = self.state["closed_trades"][-200:]

        # Circuit breaker check
        equity_now = self.equity()
        if self.state["daily_pnl"] < 0 and abs(self.state["daily_pnl"]) >= equity_now * DAILY_LOSS_LIMIT_PCT:
            self._trigger_circuit_breaker(f"Günlük zarar limiti aşıldı: {self.state['daily_pnl']:.2f} USD")

        self._save_state()
        self._log_thought(
            f"CLOSE {symbol} @ ${price:.4f} | PnL ${pnl:.2f} ({pnl_pct*100:.1f}%) | {reason}",
            "close",
            trade_record,
        )
        return {"success": True, "pnl": pnl, "pnl_pct": pnl_pct, "price": price}

    def check_stops(self) -> List[Dict]:
        """Check all open positions against stop-loss / take-profit."""
        results = []
        for symbol in list(self.state["positions"].keys()):
            pos = self.state["positions"][symbol]
            price = self.get_price(symbol)
            if not price:
                continue
            if price <= pos["stop"]:
                r = self.close_position(symbol, reason="stop_loss")
                results.append({"symbol": symbol, "event": "stop_loss", **r})
            elif price >= pos["take"]:
                r = self.close_position(symbol, reason="take_profit")
                results.append({"symbol": symbol, "event": "take_profit", **r})
        return results

    # ---------- AI decision (paper) ----------
    def analyze_and_decide(self, extra_context: str = "") -> Dict[str, Any]:
        """LLM suggests action; code enforces all risk rules."""
        if self._circuit_breaker_active():
            return {"action": "hold", "reason": "Circuit breaker active"}

        overview = self.get_market_overview()
        equity = self.equity()
        positions = list(self.state["positions"].keys())

        prompt = f"""Sen dikkatli bir kripto analistisin. SADECE paper trading önerisi ver.
Asla garantili kazanç iddia etme. Riskliyse HOLD de.

Portföy: ${equity:.2f} | Nakit: ${self.state['cash_usd']:.2f}
Açık pozisyonlar: {positions or 'yok'}
Piyasa: {overview}

Ek bağlam:
{extra_context[:1500]}

Kurallar (bunları çiğneyemezsin):
- Tek işlemde portföyün en fazla %5'i
- Şüphe varsa HOLD
- Sadece majör coinler: BTC, ETH, SOL, BNB, XRP, ADA, LINK, AVAX

Cevabını TAM OLARAK şu formatta ver (tek satır JSON):
{{"action": "buy"|"sell"|"hold", "symbol": "BTC", "confidence": 0.0-1.0, "reason": "kısa gerekçe"}}
"""
        try:
            raw = self.ollama.chat(
                prompt,
                system="Sen muhafazakar bir risk yöneticisisin. Belirsizse hold seç. JSON dışında hiçbir şey yazma.",
            )
            # Extract JSON
            import re
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                return {"action": "hold", "reason": "LLM parse edilemedi", "raw": raw[:300]}
            decision = json.loads(m.group(0))
        except Exception as e:
            return {"action": "hold", "reason": f"Analiz hatası: {e}"}

        action = str(decision.get("action", "hold")).lower()
        symbol = str(decision.get("symbol", "")).upper().replace("USDT", "")
        reason = str(decision.get("reason", ""))[:400]
        confidence = float(decision.get("confidence", 0))

        self._log_thought(f"AI decision: {action} {symbol} conf={confidence:.2f} | {reason}", "ai_decision")

        if action == "buy" and confidence >= 0.55 and symbol:
            return self.open_long(symbol, reasoning=reason)
        if action == "sell" and symbol in self.state["positions"]:
            return self.close_position(symbol, reason=f"ai_sell: {reason}")

        return {"action": "hold", "reason": reason or "Sinyal yeterince güçlü değil", "confidence": confidence}

    # ---------- status for UI ----------
    def get_status(self) -> Dict[str, Any]:
        self._reset_daily_if_needed()
        eq = self.equity()
        start = float(self.state.get("equity_start", self.starting_balance))
        positions_mtm = []
        for sym, pos in self.state["positions"].items():
            price = self.get_price(sym) or pos["entry"]
            pnl = (price - pos["entry"]) * pos["qty"]
            positions_mtm.append({
                "symbol": sym,
                "qty": pos["qty"],
                "entry": pos["entry"],
                "mark": price,
                "pnl": pnl,
                "stop": pos["stop"],
                "take": pos["take"],
                "reasoning": pos.get("reasoning", ""),
            })

        recent_thoughts = []
        if self.log_path.exists():
            try:
                lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()[-15:]
                for ln in lines:
                    recent_thoughts.append(json.loads(ln))
            except Exception:
                pass

        return {
            "mode": "paper" if not self.real_trading else "REAL (dangerous)",
            "equity": round(eq, 2),
            "cash": round(float(self.state["cash_usd"]), 2),
            "pnl_total": round(eq - start, 2),
            "pnl_total_pct": round((eq - start) / start * 100, 2) if start else 0,
            "daily_pnl": round(float(self.state.get("daily_pnl", 0)), 2),
            "open_positions": positions_mtm,
            "total_trades": self.state.get("total_trades", 0),
            "winning_trades": self.state.get("winning_trades", 0),
            "circuit_breaker": self._circuit_breaker_active(),
            "circuit_breaker_until": self.state.get("circuit_breaker_until"),
            "recent_thoughts": recent_thoughts,
            "hard_rules": {
                "max_position_pct": MAX_POSITION_PCT,
                "stop_loss_pct": DEFAULT_STOP_LOSS_PCT,
                "take_profit_pct": DEFAULT_TAKE_PROFIT_PCT,
                "daily_loss_limit_pct": DAILY_LOSS_LIMIT_PCT,
            },
        }

    def run_cycle(self, context: str = "") -> Dict[str, Any]:
        """One autonomous cycle: check stops → analyze → maybe trade."""
        stops = self.check_stops()
        decision = self.analyze_and_decide(extra_context=context)
        status = self.get_status()
        return {
            "stops_triggered": stops,
            "decision": decision,
            "status": status,
        }
