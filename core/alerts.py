import logging
import os
import asyncio
from telegram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = int(os.getenv("TELEGRAM_CHAT_ID", "0"))


class TelegramHandler(logging.Handler):
    def __init__(self, level: int = logging.ERROR) -> None:
        super().__init__(level)
        self.bot: Bot | None = Bot(TOKEN) if TOKEN else None

    def emit(self, record: logging.LogRecord) -> None:
        if not self.bot or not CHAT:
            return
        bot = self.bot
        assert bot is not None
        msg = f"\u26a0\ufe0f {record.levelname}: {record.getMessage()[:350]}"
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        async def _send() -> None:
            try:
                await bot.send_message(chat_id=CHAT, text=msg)
            except Exception:
                logging.exception("Failed to send Telegram message")

        try:
            loop.create_task(_send())
        except Exception:
            logging.exception("Failed to schedule Telegram message")
