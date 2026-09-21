"""App KCN en Flet (modo web/PWA)."""

from __future__ import annotations

import flet as ft

from kcn.ui import theme as t
from kcn.ui.state import AppState
from kcn.ui.screens.profile import build_profile
from kcn.ui.screens.today import build_today
from kcn.ui.screens.register import build_registrar
from kcn.ui.screens.progress import build_progress

TABS = [
    ("Hoy", ft.Icons.TODAY),
    ("Registrar", ft.Icons.ADD_CIRCLE_OUTLINE),
    ("Progreso", ft.Icons.INSIGHTS),
    ("Perfil", ft.Icons.PERSON),
]


def _placeholder(title: str) -> ft.Control:
    return ft.Container(
        content=ft.Text(title, size=28, weight=ft.FontWeight.BOLD),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )


def main(page: ft.Page) -> None:
    page.title = "KCN — Kcalorías y Nutrición"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = t.app_theme()
    page.bgcolor = t.BG
    page.padding = 0

    state = AppState()
    body = ft.Container(expand=True)

    def render(idx: int) -> None:
        if idx == 0:
            body.content = build_today(state, page)
        elif idx == 1:
            body.content = build_registrar(state, page)
        elif idx == 2:
            body.content = build_progress(state, page)
        elif idx == 3:
            body.content = build_profile(state, page)
        else:
            body.content = _placeholder(TABS[idx][0])


    def on_nav(e) -> None:
        render(e.control.selected_index)
        page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_nav,
        destinations=[ft.NavigationBarDestination(icon=ic, label=lbl) for lbl, ic in TABS],
    )
    render(0)
    page.add(body)