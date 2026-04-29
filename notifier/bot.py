"""
Telegram Bot Notifier - Sends daily property picks to curator.
"""

import asyncio
from typing import Optional
from loguru import logger
from dotenv import load_dotenv
import os

load_dotenv()


class TelegramNotifier:
    """Sends formatted messages via Telegram bot."""

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = f"https://api.telegram.org/bot{self.token}"

        if not self.token or not self.chat_id:
            logger.warning("Telegram credentials not configured - notifications disabled")

    async def send(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        Send message to configured chat.
        Returns True if successful.
        """
        if not self.token or not self.chat_id:
            logger.warning("Cannot send Telegram - missing credentials")
            return False

        try:
            import aiohttp

            # Telegram has 4096 char limit; split if needed
            max_len = 4000
            if len(message) > max_len:
                logger.info(f"Message too long ({len(message)} chars), splitting...")
                parts = self._split_message(message, max_len)
                for part in parts:
                    await self._send_single(part, parse_mode)
                return True
            else:
                return await self._send_single(message, parse_mode)

        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    async def _send_single(self, text: str, parse_mode: str) -> bool:
        """Send single Telegram message."""
        import aiohttp

        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': False,  # Show link previews for property URLs
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status == 200:
                    logger.debug("Telegram message sent ✓")
                    return True
                else:
                    error = await resp.text()
                    logger.error(f"Telegram API error {resp.status}: {error}")
                    return False

    def _split_message(self, text: str, max_len: int) -> List[str]:
        """Split long message into Telegram-friendly chunks."""
        parts = []
        lines = text.split('\n')
        current = ""

        for line in lines:
            if len(current) + len(line) + 1 > max_len:
                parts.append(current)
                current = line
            else:
                current += ('\n' if current else '') + line

        if current:
            parts.append(current)

        return parts

    async def send_test(self) -> bool:
        """Send test message to verify bot works."""
        test_msg = "✅ Daily Property Show bot is online and ready!"
        return await self.send(test_msg)


# Quick test function
async def test_bot():
    """Test Telegram bot connectivity."""
    notifier = TelegramNotifier()
    success = await notifier.send_test()
    if success:
        print("✓ Telegram bot configured correctly")
    else:
        print("✗ Telegram test failed - check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
    return success


if __name__ == "__main__":
    asyncio.run(test_bot())
