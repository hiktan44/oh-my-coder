from __future__ import annotations

# mypy: disable-error-code="abstract, arg-type, assignment, attr-defined, call-arg, call-overload, dict-item, func-returns-value, import-untyped, index, misc, no-any-return, no-redef, operator, override, return, return-value, syntax, union-attr, var-annotated"


"""
DingTalk (DingTalk) platform isleyicisi

destekDingTalkkurumsalicindekisimuygulama (baglanalmesaj + mesaj gonder) . 
destek: metin, Markdown, @ mesaj, kart. 

Dokumantasyon:https://open.dingtalk.com/document/orgapp/asynchronous-sending-of-enterprise-text-messages
"""


import asyncio
import contextlib
import logging
import time
from typing import TYPE_CHECKING, Optional

from ..base import IncomingMessage, OutgoingMessage, Platform, PlatformHandler

if TYPE_CHECKING:
    from starlette.requests import Request

logger = logging.getLogger(__name__)

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    logger.warning("httpx not installed. DingTalkdestekgerekister: pip install httpx")


class DingTalkHandler(PlatformHandler):
    """
    DingTalkkurumsalicindekisimuygulamaisleyici

    araciligiyla AES cozgizlibaglanalmesaj (DingTalkgeri aramamod) . 
    mesaj gonderaraciligiylaDingTalkkurumsalmesaj API. 

    Ortam degiskenleri:
        DINGTALK_APP_KEY       - uygulama AppKey
        DINGTALK_APP_SECRET    - uygulama AppSecret
        DINGTALK_TOKEN         - geri arama Token(kendi olusturulan)
        DINGTALK_AES_KEY       - geri arama EncodingAESKey (43karakter) 
        DINGTALK_WEBHOOK_PORT  - yerelgeri aramadinleme uc noktaagiz (varsayilan 8080) 
    """

    name = Platform.DINGTALK

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        token: Optional[str] = None,
        aes_key: Optional[str] = None,
        webhook_port: int = 8080,
        **kwargs,
    ):
        """
        Args:
            app_key: DingTalkuygulama AppKey (client_id) 
            app_secret: DingTalkuygulama AppSecret (client_secret) 
            token: geri arama Token
            aes_key: geri arama AES Key (43karakter) 
            webhook_port: yerelgeri aramadinleme uc noktaagiz
        """
        super().__init__(**kwargs)
        self.app_key = app_key
        self.app_secret = app_secret
        self.token = token or "oh-my-coder-dingtalk"
        self.aes_key = aes_key
        self.webhook_port = webhook_port
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._stop_event = asyncio.Event()
        self._server_task: Optional[asyncio.Task[None]] = None

    # ---- PlatformHandler uygula ----

    async def start(self) -> None:
        if not _HAS_HTTPX:
            raise RuntimeError("httpx kurulu degil. Calistirin: pip install httpx")

        await self._refresh_token()

        if self.aes_key:
            self._server_task = asyncio.create_task(self._run_webhook_server())
        else:
            logger.warning(
                "[dingtalk] No AES key configured. "
                "Set DINGTALK_AES_KEY to enable message receiving."
            )

        self._started = True
        logger.info("[dingtalk] Handler started")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._server_task:
            self._server_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._server_task
        self._started = False
        logger.info("[dingtalk] Handler stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        token = await self._get_token()
        if not token:
            return False

        url = "https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2"
        params = {"access_token": token}
        payload = {
            "agent_id": self.app_key,  # agent_id ayni app_key
            "userid_list": message.chat_id,
            "msg": {
                "msgtype": "text",
                "text": {"content": message.text[:2048]},
            },
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, params=params, json=payload)
                data = resp.json()
                if data.get("errcode") == 0:
                    return True
                logger.error(f"[dingtalk] Send failed: {data}")
                self.on_error(Exception(str(data)))
                return False
        except Exception as e:
            logger.exception(f"[dingtalk] Send error: {e}")
            self.on_error(e)
            return False

    # ---- icindekisimuygula ----

    async def _refresh_token(self) -> None:
        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url, json={"appKey": self.app_key, "appSecret": self.app_secret}
            )
            data = resp.json()
            if data.get("accessToken"):
                self._access_token = data["accessToken"]
                self._token_expires_at = time.time() + data.get("expireIn", 7200) - 300
                logger.debug("[dingtalk] Token refreshed")
            else:
                logger.error(f"[dingtalk] Token refresh failed: {data}")

    async def _get_token(self) -> Optional[str]:
        if self._access_token is None or time.time() >= self._token_expires_at:
            await self._refresh_token()
        return self._access_token

    async def _run_webhook_server(self) -> None:
        """satir HTTP servisbaglanalDingTalkgeri arama"""
        try:
            import uvicorn
            from starlette.applications import Starlette
            from starlette.responses import PlainTextResponse
            from starlette.routing import Route
        except Exception as e:
            logger.exception(f"[dingtalk] Failed to start webhook server: {e}")
            return

        async def verifyGET(request: Request) -> PlainTextResponse:
            """DingTalkgeri arama URL dogrulama"""
            try:
                import base64

                from cryptography.hazmat.primitives.ciphers import (
                    Cipher,
                    algorithms,
                    modes,
                )
                from cryptography.hazmat.primitives.padding import PKCS7

                msg_signature = request.query_params.get("signature", "")  # noqa: F841
                timestamp = request.query_params.get("timestamp", "")  # noqa: F841
                nonce = request.query_params.get("nonce", "")  # noqa: F841
                echostr = request.query_params.get("echostr", "")

                if not echostr:
                    return PlainTextResponse("")

                aes_key = base64.b64decode(self.aes_key + "=")
                cipher = Cipher(algorithms.AES(aes_key), modes.CBC(aes_key[:16]))
                decryptor = cipher.decryptor()
                decrypted_padded = (
                    decryptor.update(base64.b64decode(echostr)) + decryptor.finalize()
                )
                unpadder = PKCS7(128).unpadder()
                decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
                # kaldir 16 byterastgelemakinedizi + 4 byteuzunlukderece
                content = decrypted[20:]
                return PlainTextResponse(content.decode())
            except Exception as e:
                logger.warning(f"[dingtalk] Verify error: {e}")
                return PlainTextResponse("error", status_code=400)

        async def messagePOST(request: Request) -> PlainTextResponse:
            """baglanalmesajgeri arama"""
            body = await request.text()
            await self._handle_callback(body)
            return PlainTextResponse("success")

        app = Starlette(
            routes=[
                Route("/webhook/dingtalk", messagePOST, methods=["POST"]),
                Route("/webhook/dingtalk", verifyGET, methods=["GET"]),
            ]
        )
        config = uvicorn.Config(
            app,
            host="127.0.0.1",  # nosec B104 port=self.webhook_port, log_level="warning"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def _handle_callback(self, body: str) -> None:
        """islegeri aramamesaj"""
        import json

        try:
            data = json.loads(body)
            msg_type = data.get("msgtype", "")
            if msg_type != "text":
                return

            text = data.get("text", {}).get("content", "")
            user_id = data.get("senderStaffId", data.get("sender", ""))
            chat_id = data.get("conversationId", "")  # noqa: F841

            incoming = IncomingMessage(
                platform=Platform.DINGTALK,
                user_id=user_id,
                chat_id=user_id,
                text=text,
                raw=data,
                reply_to=data.get("msgId", ""),
            )
            self.on_message(incoming)
        except Exception as e:
            logger.exception(f"[dingtalk] Callback parse error: {e}")

    def _decrypt_msg(self, encrypted: str) -> Optional[str]:
        """AES cozgizlimesaj"""
        import base64

        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives.padding import PKCS7

            aes_key = base64.b64decode(self.aes_key + "=")
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(aes_key[:16]))
            decryptor = cipher.decryptor()
            decrypted_padded = (
                decryptor.update(base64.b64decode(encrypted)) + decryptor.finalize()
            )
            unpadder = PKCS7(128).unpadder()
            decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
            # kaldir 16 rastgelemakinebyte + 4 byte msg_len
            msg_len = int.from_bytes(decrypted[16:20], "big")
            return decrypted[20 + msg_len :].decode()
        except Exception as e:
            logger.warning(f"[dingtalk] Decrypt error: {e}")
        return None


def check_dingtalk_dependencies() -> bool:
    if not _HAS_HTTPX:
        logger.error("httpx kurulu degil: pip install httpx")
        return False
    return True
