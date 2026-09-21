"""Estado compartido de la app (conexión a la base de datos local)."""

from __future__ import annotations

from datetime import date

from kcn.data.db import connect


class AppState:
    def __init__(self) -> None:
        self.conn = connect()          # ~/.kcn/kcn.db (persistente)
        self.today = date.today()