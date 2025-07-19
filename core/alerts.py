import logging
import os
import asyncio
from telegram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID_STR = os.getenv("TELEGRAM_CHAT_ID")

# Validate chat ID properly
CHAT = None
if CHAT_ID_STR:
    try:
        chat_id = int(CHAT_ID_STR)
        if chat_id != 0:  # 0 is not a valid Telegram chat ID
            CHAT = chat_id
    except ValueError:
        logging.warning("Invalid TELEGRAM_CHAT_ID: %s", CHAT_ID_STR)


class TelegramHandler(logging.Handler):
    def __init__(self, level: int = logging.ERROR) -> None:
        super().__init__(level)
        # Only create bot if both token and valid chat ID are available
        self.bot: Bot | None = None
        if TOKEN and CHAT:
            try:
                self.bot = Bot(TOKEN)
            except Exception as exc:
                logging.warning("Failed to create Telegram bot: %s", exc)

    def emit(self, record: logging.LogRecord) -> None:
        if not CHAT:
            return
        bot = self.bot
        if bot is None:
            return
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
