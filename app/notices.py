"""Gemeinsames Vokabular fuer Warnungen und Fehler.

Warnungen halten den Ablauf nicht auf, sie erscheinen in der UI und in der
PDF-Fusszeile. Fehler brechen ab. Beide tragen einen maschinenlesbaren Code, damit
das Frontend gezielt reagieren kann, und deutschen Klartext fuer den Bediener.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Notice:
    """Eine Warnung oder ein Hinweis zu einem Rechenergebnis."""

    code: str
    message: str
    severity: str = "warn"  # "info" | "warn"


class AppError(Exception):
    """Abbruchfehler mit Code, Klartext und optionalem Feldbezug fuer die UI."""

    def __init__(self, code: str, message: str, field_name: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field_name = field_name


@dataclass
class NoticeList:
    """Sammler, damit Rechenschritte Warnungen anhaengen koennen, ohne sie zu kennen."""

    items: list[Notice] = field(default_factory=list)

    def warn(self, code: str, message: str) -> None:
        self.items.append(Notice(code, message, "warn"))

    def info(self, code: str, message: str) -> None:
        self.items.append(Notice(code, message, "info"))

    def extend(self, other: "NoticeList") -> None:
        self.items.extend(other.items)

    def as_dicts(self) -> list[dict[str, str]]:
        return [
            {"code": n.code, "message": n.message, "severity": n.severity} for n in self.items
        ]
