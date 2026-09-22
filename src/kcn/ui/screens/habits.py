"""Pantalla de Hábitos: checks diarios y rachas."""

from __future__ import annotations

from datetime import date

import flet as ft

from kcn.habits import repo as hrepo
from kcn.ui import components as comp
from kcn.ui import theme as t


def build_habits(state, page: ft.Page) -> ft.Control:
    conn = state.conn
    today = date.today()

    list_col = ft.Column(spacing=8)
    new_name = comp.num_field("Nuevo hábito (p. ej. Estirar, Leer)", "")

    def toggle(hid: int, value: bool) -> None:
        hrepo.set_done(conn, hid, today, value)
        refresh()
        page.update()

    def remove(hid: int) -> None:
        hrepo.delete_habit(conn, hid)
        refresh()
        page.update()

    def refresh() -> None:
        list_col.controls.clear()
        habits = hrepo.list_habits(conn)
        done_ids = hrepo.done_ids_for_date(conn, today)
        if not habits:
            list_col.controls.append(ft.Text("Crea tu primer hábito abajo.", color=t.MUTED))
            return
        for h in habits:
            done = h.id in done_ids
            s = hrepo.streak(conn, h.id, today)
            list_col.controls.append(ft.Row([
                ft.Checkbox(value=done, on_change=lambda e, hid=h.id: toggle(hid, e.control.value)),
                ft.Text(h.name, color=t.TEXT, expand=True),
                ft.Text(f"🔥 {s}", color=(t.ACCENT if s > 0 else t.MUTED), size=13),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=t.FAT,
                              on_click=lambda e, hid=h.id: remove(hid)),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER))

    def add(e=None) -> None:
        name = (new_name.value or "").strip()
        if not name:
            return
        hrepo.add_habit(conn, name)
        new_name.value = ""
        refresh()
        page.update()

    refresh()

    today_card = comp.card(ft.Column([comp.label("Hábitos de hoy"), list_col], spacing=10))
    add_card = comp.card(ft.Column(
        [comp.label("Añadir hábito"), new_name, comp.primary_button("Añadir", add)], spacing=10))

    return ft.Container(
        bgcolor=t.BG, expand=True, padding=16,
        content=ft.Column([today_card, add_card], scroll=ft.ScrollMode.AUTO, spacing=16,
                          horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
