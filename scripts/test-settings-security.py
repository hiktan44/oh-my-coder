"""Kullanıcının OMC dosyalarına dokunmadan web testlerini çalıştırır."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

with tempfile.TemporaryDirectory(prefix="omc-settings-tests-") as directory:
    # Bazı modüller import sırasında Path.home() altında SQLite oluşturur.
    # Yalnız bu test sürecindeki Path.home değiştirilir; HOME ortamı korunur.
    with patch.object(Path, "home", return_value=Path(directory)):
        result = pytest.main([
            "-n", "0", "--tb=short",
            str(root / "tests/test_settings_security.py"),
            str(root / "tests/test_web_app_routes.py"),
            str(root / "tests/test_web_app_more.py"),
            str(root / "tests/test_web_app_extended.py"),
        ])
sys.exit(result)
