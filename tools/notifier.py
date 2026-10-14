"""
Notification system – Console + WhatsApp (via CallMeBot free API)
"""

from __future__ import annotations

import os
import logging
from typing import Optional

import requests

logger = logging.getLogger("sentinel.notifier")


class Notifier:
    """Send reports and alerts."""

    def __init__(self):
        # CallMeBot free WhatsApp API (https://www.callmebot.com/blog/free-api-whatsapp-messages/)
        # User needs to activate once by messaging the bot
        self.whatsapp_phone = os.getenv("WHATSAPP_PHONE")  # e.g. 905xxxxxxxxx
        self.whatsapp_apikey = os.getenv("WHATSAPP_APIKEY")
        self.enabled = bool(self.whatsapp_phone and self.whatsapp_apikey)

    def send_console(self, message: str):
        print("\n" + "=" * 60)
        print(message)
        print("=" * 60)

    def send_whatsapp(self, message: str) -> bool:
        """Send message via CallMeBot free WhatsApp API."""
        if not self.enabled:
            logger.warning("WhatsApp not configured (WHATSAPP_PHONE / WHATSAPP_APIKEY missing)")
            return False

        # CallMeBot has a 1000 char limit roughly, so we truncate safely
        text = message[:900] + ("..." if len(message) > 900 else "")

        url = "https://api.callmebot.com/whatsapp.php"
        params = {
            "phone": self.whatsapp_phone,
            "text": text,
            "apikey": self.whatsapp_apikey,
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                logger.info("WhatsApp message sent successfully")
                return True
            else:
                logger.error(f"WhatsApp failed: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            logger.error(f"WhatsApp error: {e}")
            return False

    def notify(self, message: str, whatsapp: bool = True):
        """Send to console + optionally WhatsApp."""
        self.send_console(message)
        if whatsapp and self.enabled:
            self.send_whatsapp(message)
