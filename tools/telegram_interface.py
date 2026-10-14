"""
Telegram Interface — Secure bidirectional chat with Sentinel.
Only the authorized TELEGRAM_ALLOWED_USER_ID can talk to the agent.
Works on phone and desktop. Fully private.
"""

from __future__ import annotations

import logging
import os
import asyncio
from typing import Optional, Callable

logger = logging.getLogger("sentinel.telegram")

try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        filters,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed. Telegram disabled.")


class TelegramInterface:
    """Private Telegram gateway for Sentinel."""

    def __init__(
        self,
        chat_handler: Callable[[str], str],
        status_handler: Optional[Callable[[], str]] = None,
    ):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.allowed_user_id = os.getenv("TELEGRAM_ALLOWED_USER_ID")  # strict: only this user
        self.chat_handler = chat_handler
        self.status_handler = status_handler

        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN missing — Telegram disabled")
        if not self.allowed_user_id:
            logger.warning("TELEGRAM_ALLOWED_USER_ID missing — no one can talk to the bot")

    def _is_authorized(self, user_id: int) -> bool:
        if not self.allowed_user_id:
            return False
        return str(user_id) == str(self.allowed_user_id)

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Yetkisiz. Bu bot sadece sahibine özel.")
            return
        await update.message.reply_text(
            "🛡️ Sentinel aktif.\n"
            "Bana her şeyi yazabilirsin. Seni tanıyorum ve hatırlıyorum.\n"
            "/status → durum\n"
            "/help → komutlar"
        )

    async def _status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Yetkisiz.")
            return
        if self.status_handler:
            text = self.status_handler()
        else:
            text = "Sentinel çalışıyor."
        await update.message.reply_text(text)

    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            return
        await update.message.reply_text(
            "Komutlar:\n"
            "/start — başlat\n"
            "/status — durum\n"
            "/help — bu mesaj\n\n"
            "Doğal dil örnekleri:\n"
            "• Adım Ahmet\n"
            "• Bu projeyi hatırla: nexora-ai\n"
            "• Şu hatayı debug et: TypeError...\n"
            "• https://mysite.com sitesini tara\n"
            "• app.py dosyasındaki null hatasını düzelt"
        )

    async def _message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await update.message.reply_text("⛔ Yetkisiz erişim. Bu bot sadece sahibine özel.")
            logger.warning(f"Unauthorized access attempt from user_id={user_id}")
            return

        text = update.message.text.strip()
        logger.info(f"Incoming from authorized user: {text[:80]}...")

        # Show typing
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        try:
            # Run the synchronous chat_handler in executor so we don't block
            loop = asyncio.get_event_loop()
            reply = await loop.run_in_executor(None, self.chat_handler, text)
        except Exception as e:
            logger.error(f"Handler error: {e}")
            reply = f"Bir hata oluştu: {e}"

        # Telegram message limit ~4096
        if len(reply) > 4000:
            reply = reply[:3990] + "\n\n... (kısaltıldı)"

        await update.message.reply_text(reply)

    def run(self):
        """Start the bot (blocking)."""
        if not TELEGRAM_AVAILABLE:
            raise RuntimeError("python-telegram-bot is not installed. pip install python-telegram-bot")

        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

        if not self.allowed_user_id:
            raise RuntimeError(
                "TELEGRAM_ALLOWED_USER_ID is required for security. "
                "Get your user id by messaging @userinfobot on Telegram."
            )

        app = Application.builder().token(self.token).build()

        app.add_handler(CommandHandler("start", self._start))
        app.add_handler(CommandHandler("status", self._status))
        app.add_handler(CommandHandler("help", self._help))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._message))

        logger.info("Telegram bot starting (only authorized user can talk)...")
        print("🛡️  Sentinel Telegram bot is live. Only your user_id can talk to it.")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
