"""Kullanıcının OMC dosyalarına dokunmadan web testlerini çalıştırır."""

import socket
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

original_connect = socket.socket.connect


def local_only_connect(connection, address):
    if connection.family in (socket.AF_INET, socket.AF_INET6):
        raise OSError("Web regresyonlarında gerçek dış ağ bağlantısı kapalıdır.")
    return original_connect(connection, address)

with tempfile.TemporaryDirectory(prefix="omc-settings-tests-") as directory:
    # Bazı modüller import sırasında Path.home() altında SQLite oluşturur.
    # Yalnız bu test sürecindeki Path.home değiştirilir; HOME ortamı korunur.
    with patch.object(Path, "home", return_value=Path(directory)), patch.object(socket.socket, "connect", local_only_connect):
        result = pytest.main([
            "-n", "0", "--tb=short",
            str(root / "tests/test_settings_security.py"),
            str(root / "tests/test_web_app_routes.py"),
            str(root / "tests/test_web_app_more.py"),
            str(root / "tests/test_web_app_extended.py"),
        ])
sys.exit(result)
