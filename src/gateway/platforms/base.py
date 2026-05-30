from __future__ import annotations

"""
Gateway - cokplatformmesajag gecidi

destek Telegram / Discord / WhatsApp baglangiris. 
baglanalmesajsonrabirdonusturgonderver Orchestrator isle. 

tasarim: 
- Gateway: toplamyonet, tutvarvarplatformornek, birmesajyoltarafindan
- PlatformHandler: herplatformadaptor (Telegram/Discord/WhatsApp) 
- mesajformatbir: { platform, user_id, chat_id, text, raw }
"""


import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Platform(Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    WECHAT = "wechat"


@dataclass
class IncomingMessage:
    """biralogremesajformat"""

    platform: Platform
    user_id: str
    chat_id: str
    text: str
    raw: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    reply_to: Optional[str] = None  # mesaj ID (kullandegeritekrar) 


@dataclass
class OutgoingMessage:
    """birgonderogremesajformat"""

    platform: Platform
    chat_id: str
    text: str
    reply_to: Optional[str] = None  # geritekrarbaziogremesaj
    parse_mode: str = "markdown"  # veya "html"
    extra: dict[str, Any] = field(default_factory=dict)


# ---- PlatformHandler temel sinif ----


class PlatformHandler(ABC):
    """
    platform isleyicisitemel sinif. 

    altsinifuygula: 
    - start(): baslatplatformbaglabaglan/Bot
    - stop(): iyizarifdurdur
    - send(message: OutgoingMessage): mesaj gonder
    - _register_callback(): kayitustsatirmesajgeri arama
    """

    name: Platform = Platform.TELEGRAM  # altsinifuzerine yaz

    def __init__(
        self,
        on_message: Callable[[IncomingMessage], Any],
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        """
        Args:
            on_message: alkadarmesajzamangeri arama
            on_error: yanliszamangeri arama
        """
        self.on_message = on_message
        self.on_error = on_error or self._default_error_handler
        self._started = False
        self._stop_event = asyncio.Event()

    def _default_error_handler(self, err: Exception) -> None:
        logger.error(f"[{self.name.value}] Platform error: {err}")

    @abstractmethod
    async def start(self) -> None:
        """baslatplatformbaglabaglan"""
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        """durdurplatformbaglabaglan"""
        raise NotImplementedError

    @abstractmethod
    async def send(self, message: OutgoingMessage) -> bool:
        """mesaj gonder"""
        raise NotImplementedError

    @property
    def is_started(self) -> bool:
        return self._started


class NoopHandler(PlatformHandler):
    """
    bosuygula Handler (platformhenuzyapilandirmazamankullan) . 

    kayitlogancakhayirgercekbaglabaglan. 
    """

    name = Platform.TELEGRAM  # isgalkonum

    def __init__(self, platform: Platform, **kwargs):
        self.name = platform
        super().__init__(**kwargs)

    async def start(self) -> None:
        logger.info(
            f"[{self.name.value}] NoopHandler: platform not configured, skipping"
        )

    async def stop(self) -> None:
        pass

    async def send(self, message: OutgoingMessage) -> bool:
        logger.debug(f"[{self.name.value}] NoopHandler.send: {message.text[:50]}")
        return True
