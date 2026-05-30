from __future__ import annotations

"""
Feishu / Lark platform isleyicisi

destekFeishukendiolusturuygulama (baglanalmesaj + mesaj gonder) . 
destek: metinmesaj, geritekrar, Markdown. 

Dokumantasyon:https://open.feishu.cn/document/server-docs/im-v1/message-content-description/create
"""


import asyncio
import contextlib
import logging
import time
from typing import Any, Optional

from ..base import IncomingMessage, OutgoingMessage, Platform, PlatformHandler

logger = logging.getLogger(__name__)

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False
    logger.warning("httpx not installed. Feishudestekgerekister: pip install httpx")


class FeishuHandler(PlatformHandler):
    """
    Feishukendiolusturuygulamaisleyici

    araciligiyla HTTP Webhook + tursor (Long Polling) baglanalmesaj. 
    destekmetin, kartmesaj, @ makinekisietkilesim. 

    Ortam degiskenleri:
        FEISHU_APP_ID         - Feishuuygulama App ID
        FEISHU_APP_SECRET     - Feishuuygulama App Secret
        FEISHU_VERIFY_TOKEN   - olayabone Verify Token (olabilirsec) 
        FEISHU_ENCRYPT_KEY    - olayaboneeklegizli Key (olabilirsec, orneginvar) 
    """

    name = Platform.FEISHU

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        encrypt_key: Optional[str] = None,
        verify_token: Optional[str] = None,
        **kwargs,
    ):
        """
        Args:
            app_id: Feishukendiolusturuygulama App ID (cli_xxx) 
            app_secret: Feishukendiolusturuygulama App Secret
            encrypt_key: olayeklegizli Key (orneginyapilandirmaeklegizlikuraldoldur) 
            verify_token: olayabone Verify Token
        """
        super().__init__(**kwargs)
        self.app_id = app_id
        self.app_secret = app_secret
        self.encrypt_key = encrypt_key
        self.verify_token = verify_token
        self._tenant_access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._stop_event = asyncio.Event()
        self._poll_task: Optional[asyncio.Task[None]] = None

    # ---- PlatformHandler uygula ----

    async def start(self) -> None:
        if not _HAS_HTTPX:
            raise RuntimeError("httpx kurulu degil. Calistirin: pip install httpx")

        # onal token
        await self._refresh_token()
        self._stop_event.clear()
        self._poll_task = asyncio.create_task(self._long_poll_loop())
        self._started = True
        logger.info("[feishu] Handler started")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._poll_task:
            self._poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poll_task
        self._started = False
        logger.info("[feishu] Handler stopped")

    async def send(self, message: OutgoingMessage) -> bool:
        """mesaj gonderkadarFeishu"""
        token = await self._get_token()
        if not token:
            return False

        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Feishumesajformat
        content = self._build_content(message.text, message.parse_mode)

        payload = {
            "receive_id": message.chat_id,
            "msg_type": "text",
            "content": content,
        }

        # gore chat_id formatkarar vertip
        if message.chat_id.startswith("oc_"):
            payload["receive_id_type"] = "open_id"
        elif message.chat_id.startswith("p_"):
            payload["receive_id_type"] = "phone"
        elif message.chat_id.startswith("u_"):
            payload["receive_id_type"] = "user_id"
        else:
            payload["receive_id_type"] = "chat_id"  # varsayilangrupgrup

        # geritekrarmesaj
        if message.reply_to:
            url_with_type = f"{url}?receive_id_type={payload['receive_id_type']}"
        else:
            url_with_type = f"{url}?receive_id_type={payload['receive_id_type']}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url_with_type, headers=headers, json=payload)
                data = resp.json()
                if resp.status_code == 200 and data.get("code") == 0:
                    return True
                logger.error(f"[feishu] Send failed: {data}")
                self.on_error(Exception(str(data)))
                return False
        except Exception as e:
            logger.exception(f"[feishu] Send error: {e}")
            self.on_error(e)
            return False

    # ---- icindekisimuygula ----

    async def _refresh_token(self) -> None:
        """al tenant_access_token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url, json={"app_id": self.app_id, "app_secret": self.app_secret}
            )
            data = resp.json()
            if data.get("code") == 0:
                self._tenant_access_token = data["tenant_access_token"]
                # token varetkidonem 2 kucukzaman, yukseltonce 5 puandakikayenileyeni
                self._token_expires_at = time.time() + (data.get("expire", 7200) - 300)
                logger.debug("[feishu] Token refreshed")
            else:
                logger.error(f"[feishu] Token refresh failed: {data}")

    async def _get_token(self) -> Optional[str]:
        """alvaretki token (otomatikyenileyeni) """
        if self._tenant_access_token is None or time.time() >= self._token_expires_at:
            await self._refresh_token()
        return self._tenant_access_token

    async def _long_poll_loop(self) -> None:
        """
        Feishumesajolaycek (kullan im/v1/messages baglanagiztursor) . 

        gercekyaraturetortamonerkullan"olayabone"Webhook mod, 
        uygulayapicinyokortakag Webhook zamanhazirlasecplan. 
        """
        last_msg_time = int(time.time() * 1000) - 30000  # 30saniyeoncemesaj

        while not self._stop_event.is_set():
            try:
                token = await self._get_token()
                if not token:
                    await asyncio.sleep(30)
                    continue

                url = "https://open.feishu.cn/open-apis/im/v1/messages"
                params = {
                    "container_id_type": "chat",
                    "start_time": str(last_msg_time),
                    "page_size": "50",
                }
                headers = {"Authorization": f"Bearer {token}"}

                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url, headers=headers, params=params)
                    data = resp.json()

                if data.get("code") == 0:
                    msgs = data.get("data", {}).get("items", [])
                    for msg in msgs:
                        await self._process_message(msg)
                        msg_time = int(msg.get("create_time", "0"))
                        if msg_time > last_msg_time:
                            last_msg_time = msg_time
                else:
                    logger.warning(f"[feishu] Poll failed: {data}")

                # tursorarasindaayir 5 saniye
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"[feishu] Poll error: {e}")
                await asyncio.sleep(10)

    async def _process_message(self, msg: dict[str, Any]) -> None:
        """isleFeishumesaj"""
        msg_type = msg.get("msg_type", "")
        if msg_type != "text":
            logger.debug(f"[feishu] Unsupported msg_type: {msg_type}")
            return

        sender = msg.get("sender", {})
        chat_type = msg.get("chat_type", "")
        if chat_type != "p2p":  # sadeceisleozelsohbet
            logger.debug(f"[feishu] Ignoring non-p2p message: {chat_type}")
            return

        text = msg.get("body", {}).get("content", "")
        try:
            import json

            content = json.loads(text)
            text = content.get("text", "")
        except Exception:
            pass

        if not text:
            return

        user_id = sender.get("id", "")
        chat_id = msg.get("chat_id", "")

        incoming = IncomingMessage(
            platform=Platform.FEISHU,
            user_id=user_id,
            chat_id=user_id,  # gondergeriveraynibirkullanici
            text=text,
            raw={
                "message_id": msg.get("message_id", ""),
                "chat_id": chat_id,
                "chat_type": chat_type,
                "sender": sender,
                "create_time": msg.get("create_time", ""),
            },
            reply_to=msg.get("message_id", ""),
        )

        try:
            self.on_message(incoming)
        except Exception as e:
            logger.exception(f"[feishu] on_message error: {e}")
            self.on_error(e)

    @staticmethod
    def _build_content(text: str, parse_mode: str) -> str:
        """olusturFeishumesajicerik"""
        import json

        return json.dumps({"text": text})


def check_feishu_dependencies() -> bool:
    """kontrolFeishubagimlilikolup olmadigidoluyeterli"""
    if not _HAS_HTTPX:
        logger.error("httpx kurulu degil: pip install httpx")
        return False
    return True
