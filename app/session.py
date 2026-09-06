"""Kurzlebiger Speicher fuer hochgeladene Fotos und ihre Zwischenergebnisse.

Bewusst nur im Arbeitsspeicher plus ein Temp-Verzeichnis fuer die Vorschau-JPEGs:
Es gibt keine Nutzerkonten und nichts, das laenger als eine Sitzung leben soll.
Alte Sitzungen verfallen nach SESSION_TTL_S, zusaetzlich begrenzt MAX_SESSIONS den
Speicherbedarf - ein 12-MP-Foto belegt entpackt rund 36 MB.
"""

from __future__ import annotations

import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from app import config
from app.notices import AppError
from app.vision.detect import DetectedMarker, Photo

MAX_SESSIONS = 8


@dataclass
class Session:
    """Ein hochgeladenes Foto samt allem, was seither daraus berechnet wurde."""

    session_id: str
    filename: str
    photo: Photo
    directory: Path
    created_at: float = field(default_factory=time.time)
    markers: list[DetectedMarker] = field(default_factory=list)
    state: dict[str, object] = field(default_factory=dict)

    def preview_path(self, kind: str) -> Path:
        return self.directory / f"{kind}.jpg"

    def write_preview(self, kind: str, image_bgr: np.ndarray) -> Path:
        path = self.preview_path(kind)
        cv2.imwrite(str(path), image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), config.JPEG_QUALITY])
        return path


class SessionStore:
    """Sitzungsverwaltung mit TTL und Obergrenze."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._root = Path(tempfile.gettempdir()) / "aruco-homographie"
        self._root.mkdir(parents=True, exist_ok=True)

    def create(self, photo: Photo, filename: str) -> Session:
        self.purge()
        session_id = uuid.uuid4().hex
        directory = self._root / session_id
        directory.mkdir(parents=True, exist_ok=True)

        session = Session(session_id, filename, photo, directory)
        self._sessions[session_id] = session
        self._enforce_limit()
        return session

    def get(self, session_id: str) -> Session:
        self.purge()
        session = self._sessions.get(session_id)
        if session is None:
            raise AppError(
                "session_expired",
                "Die Sitzung ist abgelaufen. Bitte das Foto erneut hochladen.",
                "session_id",
            )
        return session

    def purge(self) -> None:
        deadline = time.time() - config.SESSION_TTL_S
        for session_id in [s for s, v in self._sessions.items() if v.created_at < deadline]:
            self._drop(session_id)

    def _enforce_limit(self) -> None:
        while len(self._sessions) > MAX_SESSIONS:
            oldest = min(self._sessions, key=lambda key: self._sessions[key].created_at)
            self._drop(oldest)

    def _drop(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            shutil.rmtree(session.directory, ignore_errors=True)


store = SessionStore()
