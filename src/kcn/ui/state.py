"""Estado compartido de la app (conexión a la base de datos del usuario)."""

from __future__ import annotations

from datetime import date

from kcn.data.db import connect


class AppState:
    def __init__(self, db_path=None) -> None:
        self.conn = connect(db_path) if db_path else connect()
        self.today = date.today()
        self.username = None
        self.logout = None
