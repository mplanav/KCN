"""Entrada ASGI para producción (uvicorn serve:app)."""

import flet.fastapi as flet_fastapi

from kcn.ui.app import main

app = flet_fastapi.app(main)
