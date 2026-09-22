"""App KCN — hub personal con login por usuario (Flet 1.0, web/PWA)."""

from __future__ import annotations

import flet as ft

from kcn.auth import repo as auth
from kcn.ui import theme as t
from kcn.ui.state import AppState
from kcn.ui.screens.auth import build_auth
from kcn.ui.screens.today import build_today
from kcn.ui.screens.register import build_registrar
from kcn.ui.screens.entreno import build_entreno
from kcn.ui.screens.dinero import build_dinero
from kcn.ui.screens.yo import build_yo

TABS = [
    ("Hoy", ft.Icons.TODAY),
    ("Comida", ft.Icons.RESTAURANT),
    ("Entreno", ft.Icons.FITNESS_CENTER),
    ("Dinero", ft.Icons.SAVINGS),
    ("Yo", ft.Icons.PERSON),
]


def main(page: ft.Page) -> None:
    page.title = "KCN — Mi día a día"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = t.app_theme()
    page.bgcolor = t.BG
    page.padding = 0

    def start_app(username: str) -> None:
        un = auth.normalize(username)
        state = AppState(db_path=str(auth.user_db_path(un)))
        state.username = un
        try:
            page.client_storage.set("kcn_user", un)
        except Exception:
            pass

        body = ft.Container(expand=True)
        builders = {0: build_today, 1: build_registrar, 2: build_entreno,
                    3: build_dinero, 4: build_yo}

        def render(idx: int) -> None:
            body.content = builders[idx](state, page)

        def on_nav(e) -> None:
            render(e.control.selected_index)
            page.update()

        def do_logout(e=None) -> None:
            try:
                page.client_storage.remove("kcn_user")
            except Exception:
                pass
            page.controls.clear()
            page.navigation_bar = None
            page.add(build_auth(page, start_app))
            page.update()

        state.logout = do_logout

        page.controls.clear()
        page.navigation_bar = ft.NavigationBar(
            selected_index=0, on_change=on_nav,
            destinations=[ft.NavigationBarDestination(icon=ic, label=lbl) for lbl, ic in TABS])
        render(0)
        page.add(body)
        page.update()

    remembered = None
    try:
        remembered = page.client_storage.get("kcn_user")
    except Exception:
        pass

    if remembered and auth.user_exists(remembered):
        start_app(remembered)
    else:
        page.add(build_auth(page, start_app))
