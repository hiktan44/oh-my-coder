"""Ayar yönetimi için harici yönetici anahtarı ve istek doğrulaması."""

import base64
import binascii
import os
import secrets
from urllib.parse import urlsplit

from fastapi import HTTPException, Request


def settings_admin_token() -> str:
    token = os.environ.get("OMC_API_TOKEN", "")
    if len(token.strip().encode("utf-8")) < 32:
        raise RuntimeError("OMC_API_TOKEN en az 32 baytlık harici bir anahtar olmalıdır.")
    origin = os.environ.get("OMC_SETTINGS_ORIGIN")
    if origin and _origin_identity(origin) is None:
        raise RuntimeError("OMC_SETTINGS_ORIGIN geçerli bir HTTP(S) origin olmalıdır.")
    return token


def _origin_identity(origin: str):
    try:
        source = urlsplit(origin)
        if not (
            source.scheme in ("http", "https")
            and source.username is None
            and source.password is None
            and source.path in ("", "/")
            and not source.query
            and not source.fragment
            and bool(source.hostname)
            and not any(character.isspace() for character in source.netloc)
        ):
            return None
        port = source.port if source.port is not None else (443 if source.scheme == "https" else 80)
        return source.scheme, source.hostname, port
    except ValueError:
        return None


def _same_origin(origin: str, expected: str) -> bool:
    identity = _origin_identity(origin)
    return identity is not None and identity == _origin_identity(expected)


def require_settings_admin(request: Request) -> None:
    try:
        expected = settings_admin_token().encode("utf-8")
    except RuntimeError as exc:
        raise HTTPException(503, "Yönetici erişimi yapılandırılmamış.") from exc

    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    valid = False
    if len(header) <= 4096 and scheme.lower() == "bearer":
        valid = secrets.compare_digest(value.encode("utf-8"), expected)
    elif len(header) <= 4096 and scheme.lower() == "basic":
        try:
            username, separator, password = base64.b64decode(
                value, validate=True
            ).partition(b":")
            valid = (
                secrets.compare_digest(username, b"yonetici")
                & secrets.compare_digest(password, expected)
                & bool(separator)
            )
        except (ValueError, binascii.Error):
            pass
    if not valid:
        raise HTTPException(
            401,
            "Ayarları yönetmek için yönetici girişi gerekli.",
            headers={"WWW-Authenticate": 'Basic realm="OMC Ayarlar", charset="UTF-8"'},
        )

    # Tarayıcı Basic kimlik bilgisini otomatik gönderdiği için yazma istekleri
    # başka bir sayfanın Origin değeriyle kabul edilmez. Bearer kullanan CLI
    # isteklerinde Origin başlığı bulunmayabilir.
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin is not None:
        expected_origin = os.environ.get("OMC_SETTINGS_ORIGIN") or str(request.base_url)
        if not _same_origin(origin, expected_origin):
            raise HTTPException(403, "Başka bir siteden ayar değiştirilemez.")
