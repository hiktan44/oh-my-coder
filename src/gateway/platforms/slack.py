from __future__ import annotations

"""
Slack platform isleyicisi

destek Slack Bot (Events API + Web API) . 
destek: metinmesaj, geritekrar, blokmesaj (Block Kit) , satirsurec. 

Dokumantasyon:https://api.slack.com/apis/connected
"""


import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any, Optional

from ..base import IncomingMessage, OutgoingMessage, Platform, PlatformHandler

if TYPE_CHECKING:
    from starlette.requests import Request

logger = logging.getLogger(__name__)

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    logger.warning("httpx not installed. Slack destekgerekister: pip install httpx")


class SlackHandler(PlatformHandler):
    """
    Slack Bot isleyici

    araciligiyla HTTP Webhook (Events API) baglanalmesaj. 
    araciligiyla Slack Web API mesaj gonder. 

    Ortam degiskenleri:
        SLACK_BOT_TOKEN       - xoxb-... Bot User OAuth Token
        SLACK_SIGNING_SECRET  - Slack Signing Secret (kullandedogrulamaistekkaynak) 
        SLACK_APP_TOKEN       - xapp-... App-Level Token (gerekister channels:history scope) 
        SLACK_WEBHOOK_PORT    - yerel Webhook dinleme uc noktaagiz (varsayilan 8080) 

    gerekistericinde Slack App yapilandirma: 
    1. Event Subscriptions → Enable Events → Request URL
    2. Bot Token Scopes: chat:write, channels:history, im:history, groups:history
    3. Subscribe to: message.im, message.channels, message.groups
    """

    name = Platform.SLACK

    def __init__(
        self,
        bot_token: str,
        signing_secret: str,
        app_token: Optional[str] = None,
        webhook_port: int = 8080,
        **kwargs,
    ):
        """
        Args:
            bot_token: xoxb-... Bot User OAuth Token
            signing_secret: Slack Signing Secret ( Basic Information al) 
            app_token: xapp-... App-Level Token (Socket Mode gerekister) 
            webhook_port: yerel Webhook dinleme uc noktaagiz
        """
        super().__init__(**kwargs)
        self.bot_token = bot_token
        self.signing_secret = signing_secret
        self.app_token = app_token
        self.webhook_port = webhook_port
        self._server_task: Optional[asyncio.Task[None]] = None

    # ---- PlatformHandler uygula ----

    async def start(self) -> None:
        if not _HAS_HTTPX:
            raise RuntimeError("httpx kurulu degil. Calistirin: pip install httpx")

        self._server_task = asyncio.create_task(self._run_webhook_server())
        self._started = True
        logger.info(
            f"[slack] Handler started. "
            f"Register webhook URL: http://<your-host>:{self.webhook_port}/webhook/slack"
        )

    async def stop(self) -> None:
        if self._server_task:
            self._server_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._server_task
        self._started = False
        logger.info("[slack] Handler stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        """mesaj gonderkadar Slack"""
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "channel": message.chat_id,
            "text": message.text[:3000],  # Slack sinir
        }

        if message.reply_to:
            payload["thread_ts"] = message.reply_to

        if message.parse_mode == "blocks":
            payload["blocks"] = message.extra.get("blocks", [])

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                data = resp.json()
                if data.get("ok"):
                    return True
                logger.error(f"[slack] Send failed: {data.get('error')}")
                self.on_error(Exception(data.get("error", "unknown")))
                return False
        except Exception as e:
            logger.exception(f"[slack] Send error: {e}")
            self.on_error(e)
            return False

    # ---- icindekisimuygula ----

    async def _run_webhook_server(self) -> None:
        """satir HTTP servisbaglanal Slack olay"""
        try:
            import uvicorn
            from starlette.applications import Starlette
            from starlette.responses import JSONResponse, PlainTextResponse
            from starlette.routing import Route
        except Exception as e:
            logger.exception(f"[slack] Failed to start webhook server: {e}")
            return

        async def eventsPOST(request: Request) -> JSONResponse:
            """baglanal Slack olay"""
            body = await request.json()
            await self._handle_event(body)
            return JSONResponse(content={"status": "ok"})

        async def oauthGET(request: Request) -> PlainTextResponse:
            """Slack URL dogrulama"""
            return PlainTextResponse("OK")

        app = Starlette(
            routes=[
                Route("/webhook/slack", eventsPOST, methods=["POST"]),
                Route("/webhook/slack", oauthGET, methods=["GET"]),
            ]
        )
        config = uvicorn.Config(
            app,
            host="127.0.0.1",  # nosec B104 port=self.webhook_port, log_level="warning"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def _handle_event(self, body: dict[str, Any]) -> None:
        """isle Slack olay"""
        # URL dogrulama
        if "challenge" in body:
            logger.debug("[slack] URL verification challenge received")
            return

        # isleolayliste
        events = body.get("event", {})
        event_type = events.get("type", "")

        # islemesajolay
        if event_type in ("message", "app_mention"):
            await self._process_message(events)

        # isleolaygeri arama (asenkronmod) 
        for item in body.get("event_callbacks", []):
            evt = item.get("event", {})
            if evt.get("type") == "message":
                await self._process_message(evt)

    async def _process_message(self, event: dict[str, Any]) -> None:
        """isle Slack mesajolay"""
        # yoksaymakinekisikendimesaj
        if event.get("subtype") == "bot_message":
            return
        if event.get("bot_id"):
            return

        text = event.get("text", "")
        if not text:
            return

        user_id = event.get("user", "")
        chat_id = event.get("channel", "")
        thread_ts = event.get("thread_ts", "") or event.get("ts", "")

        incoming = IncomingMessage(
            platform=Platform.SLACK,
            user_id=user_id,
            chat_id=chat_id,
            text=text,
            raw={
                "event_ts": event.get("ts", ""),
                "thread_ts": thread_ts,
                "channel_type": event.get("channel_type", "channel"),
                "team": event.get("team", ""),
            },
            reply_to=thread_ts if thread_ts != event.get("ts", "") else None,
        )

        try:
            self.on_message(incoming)
        except Exception as e:
            logger.exception(f"[slack] on_message error: {e}")
            self.on_error(e)


def check_slack_dependencies() -> bool:
    if not _HAS_HTTPX:
        logger.error("httpx kurulu degil: pip install httpx")
        return False
    return True
