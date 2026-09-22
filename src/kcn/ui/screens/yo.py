"""Pantalla 'Yo': sesión, Perfil, Progreso y Hábitos."""

from __future__ import annotations

import flet as ft

from kcn.ui import theme as t
from kcn.ui.screens.profile import build_profile
from kcn.ui.screens.progress import build_progress
from kcn.ui.screens.habits import build_habits

_BUILDERS = {"perfil": build_profile, "progreso": build_progress, "habitos": build_habits}
_LABELS = [("perfil", "Perfil"), ("progreso", "Progreso"), ("habitos", "Hábitos")]


def build_yo(state, page: ft.Page) -> ft.Control:
    holder = ft.Container(expand=True)
    seg: dict[str, ft.FilledButton] = {}

    def select(which: str, update: bool = True) -> None:
        holder.content = _BUILDERS[which](state, page)
        for key, btn in seg.items():
            active = key == which
            btn.style = ft.ButtonStyle(bgcolor=(t.ACCENT if active else t.SURFACE_2),
                                       color=(t.BG if active else t.MUTED))
        if update:
            page.update()

    for key, label in _LABELS:
        seg[key] = ft.FilledButton(content=label, expand=True,
                                   on_click=lambda e, k=key: select(k))

    top = ft.Row([ft.Text(f"Sesión: {state.username or '—'}", color=t.MUTED, size=12, expand=True),
                  ft.OutlinedButton(content="Cerrar sesión",
                                    on_click=(state.logout or (lambda e: None)),
                                    style=ft.ButtonStyle(color=t.FAT))],
                 vertical_alignment=ft.CrossAxisAlignment.CENTER)
    header = ft.Container(padding=16, content=ft.Column(
        [top, ft.Row([seg[k] for k, _ in _LABELS], spacing=8)], spacing=10))

    select("perfil", update=False)

    return ft.Container(
        bgcolor=t.BG, expand=True,
        content=ft.Column([header, holder], spacing=0, expand=True))
