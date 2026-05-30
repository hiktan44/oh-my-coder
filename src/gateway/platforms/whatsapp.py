from __future__ import annotations

"""
WhatsApp Business Cloud API platform isleyicisi

destek WhatsApp Business Cloud API (resmiyon API, yokgerekinciucyonicindearasindaogre) . 
destek: mesajbaglanal (Webhook) , mesajgondergonder. 

Dokumantasyon:https://developers.facebook.com/docs/whatsapp/cloud-api
"""


import asyncio
import contextlib
import logging
import os
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
    logger.warning("httpx not installed. WhatsApp support requires: pip install httpx")

try:
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse, PlainTextResponse
    from starlette.routing import Route

    _HAS_STARLETTE = True
except ImportError:
    _HAS_STARLETTE = False
    logger.warning(
        "starlette not installed. WhatsApp support requires: pip install starlette"
    )


# WhatsApp Cloud API uc noktasablon
_WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"


class WhatsAppHandler(PlatformHandler):
    """
    WhatsApp Business Cloud API isleyici

    baglanal Webhook olay → donusturicin IncomingMessage → iletver on_message
    mesaj gonder → WhatsApp Send API

    ortam degiskenmiktaryapilandirma: 
        WHATSAPP_PHONE_NUMBER_ID   - elektrikkonusmanokod ID (From nokod) 
        WHATSAPP_WEBHOOK_URL       - Webhook temeltemel URL (hayiriceriryol) 
        WHATSAPP_WEBHOOK_PORT      - yereldinleme uc noktaagiz (varsayilan 8080) 
        WHATSAPP_VERIFY_TOKEN      - dogrulama Token(kendi olusturulan)
        WHATSAPP_ACCESS_TOKEN      - Long-lived Access Token

    yerelsatirsonragerek http://<your-host>:<port>/webhook/whatsapp kayitkadar Meta Webhook. 
    """

    name = Platform.WHATSAPP

    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        webhook_url: str,
        verify_token: Optional[str] = None,
        webhook_port: int = 8080,
        **kwargs,
    ):
        """
        Args:
            phone_number_id: WhatsApp ticaretendustrielektrikkonusmanokod ID (From nokod) 
            access_token: Meta App Access Token (Long-lived) 
            webhook_url: senservisortakag URL (kullandekayit Webhook) 
            verify_token: Webhook dogrulama Token (kendiolustur, kullandekontroldogrula Meta dogrulamaistek) 
            webhook_port: yerel Webhook dinleme uc noktaagiz
        """
        super().__init__(**kwargs)
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.webhook_url = webhook_url.rstrip("/")
        self.verify_token = verify_token or os.environ.get(
            "WHATSAPP_VERIFY_TOKEN", "oh-my-coder-verify"
        )
        self.webhook_port = webhook_port
        self._app: Any = None
        self._server_task: Optional[asyncio.Task[None]] = None

    # ---- PlatformHandler uygula ----

    async def start(self) -> None:
        if not _HAS_STARLETTE:
            raise RuntimeError("starlette kurulu degil. Calistirin: pip install starlette httpx")

        if not _HAS_HTTPX:
            raise RuntimeError("httpx kurulu degil. Calistirin: pip install httpx")

        # olustur Webhook yoltarafindan
        async def webhookGET(request: Request) -> PlainTextResponse:
            """Meta Webhook dogrulama (GET) """
            mode = request.query_params.get("hub.mode")
            token = request.query_params.get("hub.verify_token")
            challenge = request.query_params.get("hub.challenge")

            if mode == "subscribe" and token == self.verify_token:
                logger.info("[whatsapp] Webhook verified successfully")
                return PlainTextResponse(content=challenge or "OK")
            logger.warning(
                f"[whatsapp] Webhook verify failed: mode={mode}, token={token}"
            )
            return PlainTextResponse(content="Invalid verify", status_code=403)

        async def webhookPOST(request: Request) -> JSONResponse:
            """baglanal WhatsApp mesajolay"""
            body = await request.json()
            await self._handle_webhook_event(body)
            return JSONResponse(content={"status": "ok"})

        self._app = Starlette(
            routes=[
                Route("/webhook/whatsapp", webhookPOST, methods=["POST"]),
                Route("/webhook/whatsapp", webhookGET, methods=["GET"]),
            ]
        )

        # baslatsonraplatform HTTP servis
        import uvicorn

        config = uvicorn.Config(
            self._app,
            host="127.0.0.1",  # nosec B104
            port=self.webhook_port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        self._server_task = asyncio.create_task(server.serve())
        self._started = True
        logger.info(
            f"[whatsapp] Handler started. "
            f"Register webhook URL: {self.webhook_url}/webhook/whatsapp"
        )
        logger.info(
            f"[whatsapp] Verify token: {self.verify_token} "
            f"(used when subscribing webhook in Meta Developer Console)"
        )

    async def stop(self) -> None:
        if self._server_task:
            self._server_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._server_task
        self._started = False
        logger.info("[whatsapp] Handler stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        """araciligiyla WhatsApp Cloud API mesaj gonder"""
        if not _HAS_HTTPX:
            return False

        url = f"{_WHATSAPP_API_URL}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": message.chat_id,
            "type": "text",
            "text": {"body": message.text[:4096]},  # WhatsApp sinir 4096 karakter
        }
        if message.reply_to:
            payload["context"] = {"message_id": message.reply_to}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    return True
                logger.error(f"[whatsapp] Send failed: {resp.status_code} {resp.text}")
                self.on_error(Exception(f"HTTP {resp.status_code}"))
                return False
        except Exception as e:
            logger.exception(f"[whatsapp] Send error: {e}")
            self.on_error(e)
            return False

    # ---- icindekisimisle ----

    async def _handle_webhook_event(self, body: dict[str, Any]) -> None:
        """isle WhatsApp Webhook olay"""
        try:
            entries = body.get("entry", [])
            for entry in entries:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" not in value:
                        continue

                    for msg in value.get("messages", []):
                        await self._process_message(msg, value)

        except Exception as e:
            logger.exception(f"[whatsapp] Webhook parse error: {e}")
            self.on_error(e)

    async def _process_message(
        self, msg: dict[str, Any], value: dict[str, Any]
    ) -> None:
        """isletekilogremesaj"""
        msg_type = msg.get("type")
        if msg_type != "text":
            logger.debug(f"[whatsapp] Unsupported message type: {msg_type}")
            return

        text = msg.get("text", {}).get("body", "")
        if not text:
            return

        from_id = msg.get("from", "")
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id", "")

        incoming = IncomingMessage(
            platform=Platform.WHATSAPP,
            user_id=from_id,
            chat_id=from_id,  # WhatsApp biricinbir/grupgrup ID
            text=text,
            raw={
                "message_id": msg.get("id", ""),
                "timestamp": msg.get("timestamp", ""),
                "from": from_id,
                "phone_number_id": phone_number_id,
                "profile_name": value.get("contacts", [{}])[0]
                .get("profile", {})
                .get("name", ""),
            },
            reply_to=msg.get("id", ""),
        )

        try:
            self.on_message(incoming)
        except Exception as e:
            logger.exception(f"[whatsapp] on_message error: {e}")
            self.on_error(e)


def check_whatsapp_dependencies() -> bool:
    """kontrol WhatsApp bagimlilikolup olmadigidoluyeterli"""
    if not _HAS_HTTPX:
        logger.error("httpx kurulu degil: pip install httpx")
        return False
    if not _HAS_STARLETTE:
        logger.error("starlette kurulu degil: pip install starlette")
        return False
    return True
