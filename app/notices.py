"""Gemeinsames Vokabular fuer Warnungen und Fehler.

Warnungen halten den Ablauf nicht auf, sie erscheinen in der UI und in der
PDF-Fusszeile. Fehler brechen ab. Beide tragen einen Code und benannte Parameter -
KEINEN fertigen Satz. Der Satz entsteht erst am Rand (HTTP-Antwort, PDF) aus dem
Sprachkatalog, sodass dieselbe Warnung deutsch oder englisch herauskommt, ohne dass
die Rechenschritte davon etwas wissen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app import config
from app.i18n import plain_params, translate


@dataclass(frozen=True)
class Notice:
    """Eine Warnung oder ein Hinweis zu einem Rechenergebnis."""

    code: str
    params: dict[str, object] = field(default_factory=dict)
    severity: str = "warn"  # "info" | "warn"

    def message(self, locale: str = config.DEFAULT_LOCALE) -> str:
        return translate(f"notices.{self.code}", locale, **self.params)


class AppError(Exception):
    """Abbruchfehler mit Code, Parametern und optionalem Feldbezug fuer die UI."""

    def __init__(self, code: str, field_name: str | None = None, **params: object) -> None:
        super().__init__(code)
        self.code = code
        self.field_name = field_name
        self.params = params

    def message(self, locale: str = config.DEFAULT_LOCALE) -> str:
        return translate(f"errors.{self.code}", locale, **self.params)


@dataclass
class NoticeList:
    """Sammler, damit Rechenschritte Warnungen anhaengen koennen, ohne sie zu kennen."""

    items: list[Notice] = field(default_factory=list)

    def warn(self, code: str, **params: object) -> None:
        self.items.append(Notice(code, params, "warn"))

    def info(self, code: str, **params: object) -> None:
        self.items.append(Notice(code, params, "info"))

    def extend(self, other: "NoticeList") -> None:
        self.items.extend(other.items)

    def as_dicts(self, locale: str = config.DEFAULT_LOCALE) -> list[dict[str, object]]:
        """Fuer die HTTP-Antwort. Der fertige Satz bleibt drin, damit /api/docs und
        jeder Nicht-Browser-Verbraucher lesbar bleiben - gerendert aus demselben
        Katalog, den auch die Oberflaeche benutzt."""
        return [
            {
                "code": notice.code,
                "params": plain_params(notice.params, locale),
                "severity": notice.severity,
                "message": notice.message(locale),
            }
            for notice in self.items
        ]
