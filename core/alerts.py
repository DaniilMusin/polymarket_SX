import logging
import os
import asyncio
from telegram import Bot
from logging import LogRecord
from typing import cast

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = int(os.getenv("TELEGRAM_CHAT_ID", "0"))


class TelegramHandler(logging.Handler):
    def __init__(self, level: int = logging.ERROR) -> None:
        super().__init__(level)
        self.bot: Bot = Bot(cast(str, TOKEN))

    def emit(self, record: LogRecord) -> None:
        if not TOKEN or not CHAT:
            return
        msg = f"\u26a0\ufe0f {record.levelname}: {record.getMessage()[:350]}"
        asyncio.create_task(self.bot.send_message(chat_id=CHAT, text=msg))
