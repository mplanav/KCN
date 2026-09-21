"""Componentes de UI reutilizables (tarjetas, tiles, campos, botones)."""

from __future__ import annotations

import flet as ft

from kcn.ui import theme as t


def card(content: ft.Control, padding: int = 20) -> ft.Container:
    return ft.Container(content=content, bgcolor=t.SURFACE,
                        border_radius=t.RADIUS, padding=padding)


def label(text: str) -> ft.Text:
    return ft.Text(text.upper(), size=12, weight=ft.FontWeight.BOLD, color=t.MUTED)


def stat_tile(name: str, value: str, color: str) -> ft.Container:
    return ft.Container(
        expand=True, bgcolor=t.SURFACE_2, border_radius=14, padding=14,
        content=ft.Column(
            [ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=color),
             ft.Text(name, size=11, color=t.MUTED)],
            spacing=2),
    )


def num_field(label_text: str, value: str) -> ft.TextField:
    return ft.TextField(label=label_text, value=value, filled=True,
                        border_radius=12, bgcolor=t.SURFACE_2)


def primary_button(text: str, on_click) -> ft.FilledButton:
    return ft.FilledButton(content=text, on_click=on_click,
                           style=ft.ButtonStyle(bgcolor=t.ACCENT, color=t.BG))

def macro_bar(name: str, consumed: int, target: int, color: str) -> ft.Column:
    ratio = (consumed / target) if target > 0 else 0.0
    return ft.Column(
        [ft.Row([ft.Text(name, color=t.TEXT),
                 ft.Text(f"{consumed} / {target} g", color=t.MUTED, size=12)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
         ft.ProgressBar(value=min(max(ratio, 0), 1), color=color, bgcolor=t.SURFACE_2)],
        spacing=6)


def secondary_button(text: str, on_click) -> ft.OutlinedButton:
    return ft.OutlinedButton(content=text, on_click=on_click,
                             style=ft.ButtonStyle(color=t.ACCENT))

def list_item(title: str, subtitle: str, on_click) -> ft.Container:
    return ft.Container(
        on_click=on_click, bgcolor=t.SURFACE_2, border_radius=12, padding=12, ink=True,
        content=ft.Column(
            [ft.Text(title, color=t.TEXT, weight=ft.FontWeight.W_500),
             ft.Text(subtitle, color=t.MUTED, size=12)], spacing=2))