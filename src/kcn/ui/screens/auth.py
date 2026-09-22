"""Pantalla de inicio de sesión y registro (con código de invitación)."""

from __future__ import annotations

import flet as ft

from kcn.auth import repo as auth
from kcn.ui import components as comp
from kcn.ui import theme as t


def build_auth(page: ft.Page, on_success) -> ft.Control:
    mode = {"v": "login"}
    title = ft.Text("Iniciar sesión", size=24, weight=ft.FontWeight.BOLD, color=t.TEXT)
    user = comp.num_field("Usuario", "")
    pwd = ft.TextField(label="Contraseña", password=True, can_reveal_password=True,
                       filled=True, bgcolor=t.SURFACE_2)
    invite = comp.num_field("Código de invitación", "")
    invite.visible = False
    status = ft.Text("", size=13, color=t.FAT)

    def toggle(e=None) -> None:
        reg = mode["v"] == "login"
        mode["v"] = "register" if reg else "login"
        reg = mode["v"] == "register"
        title.value = "Crear cuenta" if reg else "Iniciar sesión"
        invite.visible = reg
        submit.content = "Crear cuenta" if reg else "Entrar"
        switch.content = "¿Ya tienes cuenta? Inicia sesión" if reg else "¿No tienes cuenta? Crear una"
        status.value = ""
        page.update()

    def do(e=None) -> None:
        u = (user.value or "").strip()
        p = pwd.value or ""
        if not u or not p:
            status.value = "Usuario y contraseña obligatorios."
            page.update()
            return
        if mode["v"] == "login":
            if auth.verify_user(u, p):
                on_success(u)
            else:
                status.value = "Usuario o contraseña incorrectos."
                page.update()
        else:
            if (invite.value or "").strip() != auth.invite_code():
                status.value = "Código de invitación incorrecto."
                page.update()
                return
            try:
                auth.create_user(u, p)
                on_success(u)
            except ValueError as ex:
                status.value = str(ex)
                page.update()

    submit = comp.primary_button("Entrar", do)
    switch = ft.TextButton(content="¿No tienes cuenta? Crear una", on_click=toggle)

    card = comp.card(ft.Column(
        [ft.Text("KCN", size=30, weight=ft.FontWeight.BOLD, color=t.ACCENT),
         title, user, pwd, invite, submit, switch, status], spacing=12))

    return ft.Container(
        bgcolor=t.BG, expand=True, alignment=ft.Alignment.CENTER, padding=24,
        content=ft.Container(width=380, content=card))
