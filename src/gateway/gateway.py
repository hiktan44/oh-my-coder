from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
Gateway - cokplatformbirmesajag gecidi

Sorumluluk:
1. yonetvarplatform isleyicisi (Telegram/Discord/WhatsApp) 
2. baglanalgelkendiherplatformmesaj, birdonusturicin IncomingMessage
3. donusturgonderver Orchestrator isle
4. donussonuckadarkarsilik gelenplatform

kullanyontem: 
```python
gateway = Gateway(
    orchestrator=orch,
    telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
    discord_token=os.getenv("DISCORD_BOT_TOKEN"),
)

# yontem 1: komutsatirbaslat
await gateway.start_all()

# yontem 2: Flask/FastAPI setol
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    await gateway.handle_telegram_update(await request.json())
```

CLI:
    omc gateway start --telegram <token>
    omc gateway start --discord <token>
    omc gateway status
"""


import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from .base import (
    IncomingMessage,
    NoopHandler,
    OutgoingMessage,
    Platform,
    PlatformHandler,
)

logger = logging.getLogger(__name__)


class Gateway:
    """
    cokplatformmesajag gecidi

    yaratkomuthaftadonem: 
    1. __init__: yapilandirmaherplatform
    2. start_all(): baslatvaryapilandirmaplatform
    3. on_platform_message(): baglanalmesaj → Orchestrator → geritekrar
    4. stop_all(): durdurvarplatform
    """

    def __init__(
        self,
        orchestrator: Any = None,
        telegram_token: Optional[str] = None,
        discord_token: Optional[str] = None,
        whatsapp_phone_number_id: Optional[str] = None,
        whatsapp_access_token: Optional[str] = None,
        whatsapp_webhook_url: Optional[str] = None,
        whatsapp_verify_token: Optional[str] = None,
        feishu_app_id: Optional[str] = None,
        feishu_app_secret: Optional[str] = None,
        feishu_encrypt_key: Optional[str] = None,
        wecom_corp_id: Optional[str] = None,
        wecom_agent_id: Optional[str] = None,
        wecom_corp_secret: Optional[str] = None,
        wecom_token: Optional[str] = None,
        wecom_encoding_aes_key: Optional[str] = None,
        dingtalk_app_key: Optional[str] = None,
        dingtalk_app_secret: Optional[str] = None,
        dingtalk_token: Optional[str] = None,
        dingtalk_aes_key: Optional[str] = None,
        slack_bot_token: Optional[str] = None,
        slack_signing_secret: Optional[str] = None,
        allowed_user_ids: Optional[dict[Platform, list[str]]] = None,
        plugins_dir: Optional[Path] = None,
    ):
        """
        Args:
            orchestrator: Orchestrator ornek (kullandeislemesaj) 
            telegram_token: Telegram Bot Token
            discord_token: Discord Bot Token
            allowed_user_ids: herplatformbeyazisimtekilkullanici ID
            plugins_dir: eklentidizin (onkal) 
        """
        self.orchestrator = orchestrator
        self._handlers: dict[Platform, PlatformHandler] = {}
        self._started_platforms: list[str] = []
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()

        allowed_user_ids = allowed_user_ids or {}

        # ---- Telegram ----
        if telegram_token:
            self._register_telegram(
                telegram_token, allowed_user_ids.get(Platform.TELEGRAM, [])
            )
        else:
            self._handlers[Platform.TELEGRAM] = NoopHandler(
                platform=Platform.TELEGRAM, on_message=self._noop_handler
            )

        # ---- Discord ----
        if discord_token:
            self._register_discord(
                discord_token, allowed_user_ids.get(Platform.DISCORD, [])
            )
        else:
            self._handlers[Platform.DISCORD] = NoopHandler(
                platform=Platform.DISCORD, on_message=self._noop_handler
            )

        # ---- WhatsApp ----
        if whatsapp_phone_number_id and whatsapp_access_token:
            self._register_whatsapp(
                whatsapp_phone_number_id,
                whatsapp_access_token,
                whatsapp_webhook_url or "",
                whatsapp_verify_token,
            )
        else:
            self._handlers[Platform.WHATSAPP] = NoopHandler(
                platform=Platform.WHATSAPP, on_message=self._noop_handler
            )

        # ---- Feishu ----
        if feishu_app_id and feishu_app_secret:
            self._register_feishu(feishu_app_id, feishu_app_secret, feishu_encrypt_key)
        else:
            self._handlers[Platform.FEISHU] = NoopHandler(
                platform=Platform.FEISHU, on_message=self._noop_handler
            )

        # ---- WeCom ----
        if wecom_corp_id and wecom_agent_id and wecom_corp_secret:
            self._register_wecom(
                wecom_corp_id,
                wecom_agent_id,
                wecom_corp_secret,
                wecom_token,
                wecom_encoding_aes_key,
            )
        else:
            self._handlers[Platform.WECOM] = NoopHandler(
                platform=Platform.WECOM, on_message=self._noop_handler
            )

        # ---- DingTalk ----
        if dingtalk_app_key and dingtalk_app_secret:
            self._register_dingtalk(
                dingtalk_app_key,
                dingtalk_app_secret,
                dingtalk_token,
                dingtalk_aes_key,
            )
        else:
            self._handlers[Platform.DINGTALK] = NoopHandler(
                platform=Platform.DINGTALK, on_message=self._noop_handler
            )

        # ---- Slack ----
        if slack_bot_token and slack_signing_secret:
            self._register_slack(slack_bot_token, slack_signing_secret)
        else:
            self._handlers[Platform.SLACK] = NoopHandler(
                platform=Platform.SLACK, on_message=self._noop_handler
            )

    # ---- platformkayit ----

    def _register_telegram(self, token: str, allowed_user_ids: list[str]) -> None:
        from .platforms.telegram import TelegramHandler, check_telegram_dependencies

        if not check_telegram_dependencies():
            logger.warning("[gateway] Telegram bagimlilikeksik, atlakayit")
            return

        self._handlers[Platform.TELEGRAM] = TelegramHandler(
            bot_token=token,
            allowed_user_ids=allowed_user_ids,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/telegram] {e}"),
        )
        logger.info("[gateway] Telegram handler registered")

    def _register_discord(self, token: str, allowed_guild_ids: list[int]) -> None:
        from .platforms.discord import DiscordHandler, check_discord_dependencies

        if not check_discord_dependencies():
            logger.warning("[gateway] Discord bagimlilikeksik, atlakayit")
            return

        self._handlers[Platform.DISCORD] = DiscordHandler(
            bot_token=token,
            allowed_guild_ids=allowed_guild_ids,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/discord] {e}"),
        )
        logger.info("[gateway] Discord handler registered")

    def _register_whatsapp(
        self,
        phone_number_id: str,
        access_token: str,
        webhook_url: str,
        verify_token: Optional[str],
    ) -> None:
        from .platforms.whatsapp import WhatsAppHandler, check_whatsapp_dependencies

        if not check_whatsapp_dependencies():
            logger.warning("[gateway] WhatsApp bagimlilikeksik, atlakayit")
            return

        self._handlers[Platform.WHATSAPP] = WhatsAppHandler(
            phone_number_id=phone_number_id,
            access_token=access_token,
            webhook_url=webhook_url,
            verify_token=verify_token,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/whatsapp] {e}"),
        )
        logger.info("[gateway] WhatsApp handler registered")

    def _register_feishu(
        self, app_id: str, app_secret: str, encrypt_key: Optional[str]
    ) -> None:
        from .platforms.feishu import FeishuHandler, check_feishu_dependencies

        if not check_feishu_dependencies():
            logger.warning("[gateway] Feishubagimlilikeksik, atlakayit")
            return

        self._handlers[Platform.FEISHU] = FeishuHandler(
            app_id=app_id,
            app_secret=app_secret,
            encrypt_key=encrypt_key,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/feishu] {e}"),
        )
        logger.info("[gateway] Feishu handler registered")

    def _register_wecom(
        self,
        corp_id: str,
        agent_id: str,
        corp_secret: str,
        token: Optional[str],
        encoding_aes_key: Optional[str],
    ) -> None:
        from .platforms.wecom import WeComHandler, check_wecom_dependencies

        if not check_wecom_dependencies():
            logger.warning("[gateway] WeCombagimlilikeksik, atlakayit")
            return

        self._handlers[Platform.WECOM] = WeComHandler(
            corp_id=corp_id,
            agent_id=agent_id,
            corp_secret=corp_secret,
            token=token,
            encoding_aes_key=encoding_aes_key,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/wecom] {e}"),
        )
        logger.info("[gateway] WeCom handler registered")

    def _register_dingtalk(
        self,
        app_key: str,
        app_secret: str,
        token: Optional[str],
        aes_key: Optional[str],
    ) -> None:
        from .platforms.dingtalk import DingTalkHandler, check_dingtalk_dependencies

        if not check_dingtalk_dependencies():
            logger.warning("[gateway] DingTalkbagimlilikeksik, atlakayit")
            return

        self._handlers[Platform.DINGTALK] = DingTalkHandler(
            app_key=app_key,
            app_secret=app_secret,
            token=token,
            aes_key=aes_key,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/dingtalk] {e}"),
        )
        logger.info("[gateway] DingTalk handler registered")

    def _register_slack(self, bot_token: str, signing_secret: str) -> None:
        from .platforms.slack import SlackHandler, check_slack_dependencies

        if not check_slack_dependencies():
            logger.warning("[gateway] Slack bagimlilikeksik, atlakayit")
            return

        self._handlers[Platform.SLACK] = SlackHandler(
            bot_token=bot_token,
            signing_secret=signing_secret,
            on_message=self.on_platform_message,
            on_error=lambda e: logger.error(f"[gateway/slack] {e}"),
        )
        logger.info("[gateway] Slack handler registered")

    # ---- mesajisle ----

    def on_platform_message(self, message: IncomingMessage) -> None:
        """
        alkadarherplatformmesajzamangeri arama. 

        varsayilanuygula: yazdirlog. 
        altsinif/disindakisimolabiliruzerine yazbuyontembaglangirisgercek Orchestrator. 

        Args:
            message: birformatalogremesaj
        """
        logger.info(
            f"[gateway] [{message.platform.value}] {message.user_id}: {message.text[:80]}"
        )

        if self.orchestrator is None:
            logger.debug("[gateway] No orchestrator configured, skipping processing")
            return

        # asenkronisle (hayirbloklaplatformgeri arama) 
        asyncio.create_task(self._process_message(message))

    async def _process_message(self, message: IncomingMessage) -> None:
        """islemesaj → Orchestrator → geritekrar"""
        try:
            if self.orchestrator is None:
                return

            # olustur context
            context = {
                "task": message.text,
                "project_path": str(Path.cwd()),
                "_platform": message.platform.value,
                "_user_id": message.user_id,
                "_chat_id": message.chat_id,
            }

            # yurutis akisi
            result = await self.orchestrator.execute_workflow(
                "autopilot",
                context,
            )

            # cikarsonucmetin
            response_text = self._extract_response(result)

            # gondergeriplatform
            reply = OutgoingMessage(
                platform=message.platform,
                chat_id=message.chat_id,
                text=response_text,
                reply_to=message.reply_to,
            )
            handler = self._handlers.get(message.platform)
            if handler and handler.is_started:
                await handler.send(reply)

        except Exception as e:
            logger.exception(f"[gateway] _process_message error: {e}")
            # denegonderhatageritekrar
            try:
                error_reply = OutgoingMessage(
                    platform=message.platform,
                    chat_id=message.chat_id,
                    text=f"⚠️ islebasarisiz: {type(e).__name__}",
                )
                handler = self._handlers.get(message.platform)
                if handler and handler.is_started:
                    await handler.send(error_reply)
            except Exception:
                pass

    @staticmethod
    def _extract_response(result: Any) -> str:
        """ WorkflowResult cikaryanitmetin"""
        if result is None:
            return " (yoksonuc) "

        # dene outputs
        if hasattr(result, "outputs") and result.outputs:
            parts = []
            for agent_name, output in result.outputs.items():
                content = getattr(output, "result", None)
                if content:
                    parts.append(f"**[{agent_name}]**\n{content[:500]}")
            if parts:
                return "\n\n".join(parts)

        # dusurseviye: dogrubaglan str
        return str(result)[:1000]

    # ---- yaratkomuthaftadonem ----

    async def start_all(self) -> None:
        """baslatvaryapilandirmaplatform"""
        async with self._lock:
            tasks = []
            for platform, handler in self._handlers.items():
                if not handler.is_started:
                    tasks.append(self._start_platform(platform, handler))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        started = [p for p, h in self._handlers.items() if h.is_started]
        logger.info(f"[gateway] Started platforms: {[p.value for p in started]}")

    async def _start_platform(
        self, platform: Platform, handler: PlatformHandler
    ) -> None:
        try:
            await handler.start()
            self._started_platforms.append(platform.value)
        except Exception as e:
            logger.exception(f"[gateway] Failed to start {platform.value}: {e}")

    async def stop_all(self) -> None:
        """durdurvarplatform"""
        async with self._lock:
            tasks = []
            for platform, handler in self._handlers.items():
                if handler.is_started:
                    tasks.append(self._stop_platform(platform, handler))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        self._stop_event.set()
        logger.info("[gateway] All platforms stopped")

    async def _stop_platform(
        self, platform: Platform, handler: PlatformHandler
    ) -> None:
        try:
            await handler.stop()
            if platform.value in self._started_platforms:
                self._started_platforms.remove(platform.value)
        except Exception as e:
            logger.exception(f"[gateway] Error stopping {platform.value}: {e}")

    # ---- durumsorgu ----

    def status(self) -> dict[str, Any]:
        """donusag gecididurum"""
        handlers_info = {
            platform.value: {
                "configured": handler.__class__ != NoopHandler,
                "started": handler.is_started,
                "type": handler.__class__.__name__,
            }
            for platform, handler in self._handlers.items()
        }
        return {
            "started_platforms": self._started_platforms,
            "handlers": handlers_info,
        }

    def get_handler(self, platform: Platform) -> Optional[PlatformHandler]:
        return self._handlers.get(platform)

    def _noop_handler(self, message: IncomingMessage) -> None:
        """NoopHandler  on_message geri arama"""

    # ---- Webhook destek (saglar FastAPI setol) ----

    async def handle_telegram_update(self, update: dict[str, Any]) -> None:
        """
        isle Telegram Webhook guncelle. 

        kullande FastAPI yoltarafindan: 
        @app.post("/webhook/telegram")
        async def telegram_webhook(request: Request):
            await gateway.handle_telegram_update(await request.json())
        """
        handler = self._handlers.get(Platform.TELEGRAM)
        if handler is None or isinstance(handler, NoopHandler):
            logger.warning("[gateway] Telegram not configured")
            return

        # Telegram Webhook gerekister Update cikar message
        message_data = update.get("message", {})
        if not message_data:
            return

        from .base import IncomingMessage

        incoming = IncomingMessage(
            platform=Platform.TELEGRAM,
            user_id=str(message_data.get("from", {}).get("id", "")),
            chat_id=str(message_data.get("chat", {}).get("id", "")),
            text=message_data.get("text", ""),
            raw=update,
            reply_to=str(message_data.get("message_id", "")),
        )
        self.on_platform_message(incoming)
