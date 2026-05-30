from __future__ import annotations

"""
Telegram Bot platform isleyicisi

kullan python-telegram-bot kutuphaneuygula. 
destek: mesajbaglanal, mesajgondergonder, komutisle, geritekrar. 
"""


import logging
from typing import Any, Optional

from ..base import IncomingMessage, OutgoingMessage, Platform, PlatformHandler

logger = logging.getLogger(__name__)

# deneiceri aktar telegram kutuphane
try:
    from telegram import Update
    from telegram.ext import (
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

    _HAS_TELEGRAM = True
except ImportError:
    _HAS_TELEGRAM = False
    logger.warning("python-telegram-bot not installed. Telegram support disabled.")


class TelegramHandler(PlatformHandler):
    """
    Telegram Bot isleyici

    baglanalkullanicimesaj → donusturicin IncomingMessage → iletver on_message
    """

    name = Platform.TELEGRAM

    def __init__(
        self,
        bot_token: str,
        allowed_user_ids: Optional[list[str]] = None,
        **kwargs,
    ):
        """
        Args:
            bot_token: Telegram Bot Token ( @BotFather al) 
            allowed_user_ids: beyazisimtekilkullanici ID (None = hayirsinir) 
        """
        super().__init__(**kwargs)
        self.bot_token = bot_token
        self.allowed_user_ids = set(allowed_user_ids or [])
        self._app: Any = None
        self._dispatcher: Any = None

    # ---- PlatformHandler uygula ----

    async def start(self) -> None:
        if not _HAS_TELEGRAM:
            raise RuntimeError(
                "python-telegram-bot kurulu degil. Calistirin: pip install python-telegram-bot"
            )

        from telegram.ext import Application

        self._app = Application.builder().token(self.bot_token).build()

        # kayitisleyici
        self._app.add_handler(CommandHandler("start", self._handle_start))
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text)
        )

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(allowed_updates=Update.ALL_UPDATE_TYPES)
        self._started = True
        logger.info("[telegram] Bot started successfully")

    async def stop(self) -> None:
        if self._app is not None:
            await self._app.stop()
            self._started = False
            logger.info("[telegram] Bot stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        if self._app is None:
            return False

        try:
            await self._app.bot.send_message(
                chat_id=message.chat_id,
                text=message.text,
                parse_mode=message.parse_mode.upper() if message.parse_mode else None,
                reply_to_message_id=message.reply_to,
            )
            return True
        except Exception as e:
            logger.exception(f"[telegram] Send failed: {e}")
            self.on_error(e)
            return False

    # ---- icindekisimisleyici ----

    async def _handle_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """isle /start komut"""
        await update.message.reply_text(
            "👋 neselikarsilakullan Oh My Coder! \n\n"
            "mesaj gonderyaniolabilirbaslaticinkonusma. \n"
            "girdi /help goruntuleolabilirkullankomut. "
        )

    async def _handle_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """islemetinmesaj"""
        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id)
        text = update.message.text or ""

        # beyazisimtekilkontrol
        if self.allowed_user_ids and user_id not in self.allowed_user_ids:
            logger.warning(
                f"[telegram] Rejected message from unauthorized user: {user_id}"
            )
            await update.message.reply_text("⚠️ henuzveryetkikullanici")
            return

        # donusturicinbirformat
        incoming = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id=user_id,
            chat_id=chat_id,
            text=text,
            raw={
                "message_id": update.message.message_id,
                "username": update.effective_user.username,
                "first_name": update.effective_user.first_name,
            },
            reply_to=str(update.message.message_id),
        )

        try:
            self.on_message(incoming)
        except Exception as e:
            logger.exception(f"[telegram] on_message error: {e}")
            self.on_error(e)
            await update.message.reply_text("⚠️ islemesajzamanyanlis, lutfenbirazsonrayeniden dene. ")


# ---- bagimlilikkontrol ----


def check_telegram_dependencies() -> bool:
    """kontrol Telegram bagimlilikolup olmadigidoluyeterli"""
    if not _HAS_TELEGRAM:
        logger.error("python-telegram-bot kurulu degil")
        return False
    return True
