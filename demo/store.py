"""In-process desk store. One dict per user; no shared inbox."""

from __future__ import annotations

from threading import Lock
from typing import Any


SURFACES = ("mail", "files", "calendar")


def empty_desk() -> dict[str, list[dict[str, Any]]]:
    return {name: [] for name in SURFACES}


class DeskStore:
    """Partitioned store. All reads and writes take an explicit user_id."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._desks: dict[str, dict[str, list[dict[str, Any]]]] = {}

    def _partition(self, user_id: str) -> dict[str, list[dict[str, Any]]]:
        if not user_id:
            raise ValueError("user_id is required")
        if user_id not in self._desks:
            self._desks[user_id] = empty_desk()
        return self._desks[user_id]

    def desk(self, user_id: str) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            part = self._partition(user_id)
            return {name: list(part[name]) for name in SURFACES}

    def counts(self, user_id: str) -> dict[str, int]:
        d = self.desk(user_id)
        return {name: len(d[name]) for name in SURFACES}

    def write_artifacts(
        self,
        user_id: str,
        mail: dict[str, Any],
        file: dict[str, Any],
        event: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        """Bot write: three artifacts land only in user_id's partition."""
        if not user_id:
            raise ValueError("target_user is required")
        owned_mail = {**mail, "owner_id": user_id}
        owned_file = {**file, "owner_id": user_id}
        owned_event = {**event, "owner_id": user_id}
        with self._lock:
            part = self._partition(user_id)
            part["mail"].insert(0, owned_mail)
            part["files"].insert(0, owned_file)
            part["calendar"].insert(0, owned_event)
            return {name: list(part[name]) for name in SURFACES}

    def known_users(self) -> list[str]:
        with self._lock:
            return sorted(self._desks)
