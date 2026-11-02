"""Cookie 会话生命周期管理。"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from ...config import get_settings, update_runtime_settings
from .cookie_utils import normalize_xhs_cookie
from .errors import XhsAuthError
from .session_store import SessionStore


class SessionManager:
    def __init__(self, store: Optional[SessionStore] = None):
        self.store = store or SessionStore()
        self._lock = threading.RLock()
        self._migrate_legacy_cookie()

    def _migrate_legacy_cookie(self) -> None:
        """把旧的 runtime_settings 明文 Cookie 迁移到加密表。"""
        existing = self.store.get_active(include_cookie=False)
        if existing:
            # 已有加密会话时，内存中的旧配置不再保留明文。
            settings = get_settings()
            if settings.xhs_cookie:
                settings.xhs_cookie = ""
            return
        settings = get_settings()
        raw = (settings.xhs_cookie or "").strip()
        if not raw:
            return
        normalized = normalize_xhs_cookie(raw)
        if not normalized or "=" not in normalized:
            return
        self.store.import_cookie(
            normalized,
            account_label="migrated",
            note="从 runtime_settings 迁移",
        )
        # 迁移后不再从明文配置读取；runtime_settings.json 中的字段同步清空。
        settings.xhs_cookie = ""
        try:
            update_runtime_settings({"xhs_cookie": ""})
        except Exception as error:
            print(f"⚠️  清理明文小红书 Cookie 失败: {error}")
        print("🔐 小红书 Cookie 已迁移到加密会话表")

    def ensure_session(self) -> Dict[str, Any]:
        """返回可用的 active/degraded 会话；过期时要求重新登录。"""
        with self._lock:
            record = self.store.get_active(include_cookie=True)
            if not record:
                self._migrate_legacy_cookie()
                record = self.store.get_active(include_cookie=True)
            if not record:
                raise XhsAuthError("小红书 Cookie 未配置，请先在设置页导入")
            if record.get("status") == "expired":
                raise XhsAuthError("小红书 Cookie 已失效，请重新登录/导入 Cookie")
            return record

    def import_cookie(
        self,
        cookie: str,
        *,
        account_label: str = "default",
        user_agent: str = "",
    ) -> Dict[str, Any]:
        normalized = normalize_xhs_cookie(cookie)
        if not normalized or "=" not in normalized:
            raise XhsAuthError("小红书 Cookie 格式不正确")
        session_id = self.store.import_cookie(
            normalized,
            account_label=account_label or "default",
            user_agent=user_agent,
            status="active",
        )
        record = self.store.get_active(include_cookie=False) or {}
        record["id"] = session_id
        return record

    def mark_success(self, session_id: int) -> None:
        self.store.mark_success(session_id)

    def mark_auth_failure(self, session_id: int, message: str = "") -> None:
        self.store.mark_failure(session_id, status="expired", note=message)

    def mark_rate_limited(self, session_id: int, message: str = "") -> None:
        self.store.mark_failure(session_id, status="degraded", note=message)

    def mark_network_failure(self, session_id: int, message: str = "") -> None:
        self.store.mark_failure(session_id, status="degraded", note=message)

    def disable(self) -> None:
        record = self.store.get_active(include_cookie=False)
        if record:
            self.store.set_status(int(record["id"]), "disabled", "手动停用")

    def status(self) -> Dict[str, Any]:
        record = self.store.get_latest()
        if not record:
            return {
                "configured": False,
                "status": "needs_login",
                "message": "尚未导入小红书 Cookie",
            }
        record["configured"] = True
        record.pop("cookie_hash", None)
        record["cookie_masked"] = "已加密保存"
        return record


_MANAGER: Optional[SessionManager] = None
_MANAGER_LOCK = threading.Lock()


def get_session_manager() -> SessionManager:
    global _MANAGER
    if _MANAGER is None:
        with _MANAGER_LOCK:
            if _MANAGER is None:
                _MANAGER = SessionManager()
    return _MANAGER
