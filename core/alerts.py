import logging
import os
import asyncio
from telegram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = int(os.getenv("TELEGRAM_CHAT_ID", "0"))


class TelegramHandler(logging.Handler):
    def __init__(self, level=logging.ERROR):
        super().__init__(level)
        self.bot = Bot(TOKEN)

    def emit(self, record):
        if not TOKEN or not CHAT:
            return
        msg = f"\u26a0\ufe0f {record.levelname}: {record.getMessage()[:350]}"
        asyncio.create_task(self.bot.send_message(chat_id=CHAT, text=msg))
