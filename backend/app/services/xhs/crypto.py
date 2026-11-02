"""Cookie 加密存储。

优先使用 ``XHS_COOKIE_KEY``（Fernet key，URL-safe base64）；
没有配置时，在本地数据目录生成权限受限的 key 文件。
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

_DEFAULT_KEY_FILE = Path(__file__).resolve().parents[3] / "data" / "xhs_cookie.key"


class CookieCipher:
    def __init__(self, key_file: Optional[Path] = None):
        self.key_file = Path(key_file) if key_file else _DEFAULT_KEY_FILE
        self._fernet = Fernet(self._load_key())

    def _load_key(self) -> bytes:
        env_key = (os.getenv("XHS_COOKIE_KEY") or "").strip()
        if env_key:
            return env_key.encode("utf-8")
        if self.key_file.exists():
            return self.key_file.read_bytes().strip()
        key = Fernet.generate_key()
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self.key_file.write_bytes(key)
        try:
            os.chmod(self.key_file, 0o600)
        except OSError:
            pass
        return key

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(str(value).encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(str(token).encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise ValueError("Cookie 解密失败，请重新导入小红书 Cookie") from exc
