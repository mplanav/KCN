"""Pantalla de Dinero: nómina, resumen del mes, presupuestos, gastos y ahorro."""

from __future__ import annotations

from datetime import date

import flet as ft

from kcn.finance import repo as frepo
from kcn.finance.models import Expense
from kcn.ui import components as comp
from kcn.ui import theme as t

MONTHS = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _num(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _eur(x: float) -> str:
    return f"{x:.2f} €"


def build_dinero(state, page: ft.Page) -> ft.Control:
    conn = state.conn
    today = date.today()
    year, month = today.year, today.month

    income_field = comp.num_field("Nómina mensual (€)", str(frepo.get_income(conn) or ""))
    resumen_body = ft.Column(spacing=10)
    cats_body = ft.Column(spacing=10)
    cat_name = comp.num_field("Categoría (p. ej. Comida)", "")
    cat_limit = comp.num_field("Presupuesto/mes (€)", "")
    exp_amount = comp.num_field("Importe (€)", "")
    cat_dd = ft.Dropdown(label="Categoría", filled=True, bgcolor=t.SURFACE_2, options=[])
    exp_note = comp.num_field("Nota (opcional)", "")
    exp_list = ft.Column(spacing=8)
    goals_body = ft.Column(spacing=10)
    goal_name = comp.num_field("Meta (p. ej. Viaje)", "")
    goal_target = comp.num_field("Objetivo (€)", "")

    def render() -> None:
        cats = frepo.list_categories(conn)
        cat_by_id = {c.id: c for c in cats}
        spent_map = frepo.spent_by_category(conn, year, month)
        total_spent = frepo.month_spent(conn, year, month)
        income = frepo.get_income(conn)

        # Resumen
        resumen_body.controls.clear()
        avail = income - total_spent
        ratio = (total_spent / income) if income > 0 else 0.0
        resumen_body.controls.append(ft.Row(
            [ft.Text(_eur(total_spent), size=28, weight=ft.FontWeight.BOLD, color=t.FAT),
             ft.Text(f"de {_eur(income)}", color=t.MUTED)],
            vertical_alignment=ft.CrossAxisAlignment.END, spacing=8))
        resumen_body.controls.append(ft.ProgressBar(
            value=min(max(ratio, 0), 1), color=(t.FAT if ratio > 1 else t.ACCENT), bgcolor=t.SURFACE_2))
        resumen_body.controls.append(ft.Text(
            f"Disponible: {_eur(avail)}", color=(t.ACCENT if avail >= 0 else t.FAT),
            weight=ft.FontWeight.W_500))

        # Opciones del desplegable de categorías
        cat_dd.options = ([ft.DropdownOption(key="", text="Sin categoría")]
                          + [ft.DropdownOption(key=str(c.id), text=c.name) for c in cats])
        if cat_dd.value is None:
            cat_dd.value = ""

        # Presupuestos
        cats_body.controls.clear()
        if not cats:
            cats_body.controls.append(ft.Text("Sin categorías todavía.", color=t.MUTED))
        for c in cats:
            sp = spent_map.get(c.id, 0.0)
            r = (sp / c.monthly_limit) if c.monthly_limit > 0 else 0.0
            cats_body.controls.append(ft.Column([
                ft.Row([ft.Text(c.name, color=t.TEXT, weight=ft.FontWeight.W_500, expand=True),
                        ft.Text(f"{_eur(sp)} / {_eur(c.monthly_limit)}", color=t.MUTED, size=12),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=t.FAT,
                                      on_click=lambda e, cid=c.id: (frepo.delete_category(conn, cid),
                                                                    render(), page.update()))],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.ProgressBar(value=min(max(r, 0), 1), color=(t.FAT if r > 1 else t.ACCENT),
                               bgcolor=t.SURFACE_2)], spacing=4))

        # Gastos del mes
        exp_list.controls.clear()
        exps = frepo.expenses_for_month(conn, year, month)
        if not exps:
            exp_list.controls.append(ft.Text("Sin gastos este mes.", color=t.MUTED))
        for ex in exps:
            cname = cat_by_id[ex.category_id].name if ex.category_id in cat_by_id else "—"
            label = f"{ex.on.strftime('%d/%m')} · {cname}" + (f" · {ex.note}" if ex.note else "")
            exp_list.controls.append(ft.Row([
                ft.Text(label, color=t.MUTED, size=12, expand=True),
                ft.Text(_eur(ex.amount), color=t.TEXT, size=12),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=t.FAT,
                              on_click=lambda e, eid=ex.id: (frepo.delete_expense(conn, eid),
                                                             render(), page.update()))],
                vertical_alignment=ft.CrossAxisAlignment.CENTER))

        # Metas de ahorro
        goals_body.controls.clear()
        goals = frepo.list_goals(conn)
        if not goals:
            goals_body.controls.append(ft.Text("Sin metas de ahorro.", color=t.MUTED))
        for g in goals:
            r = (g.saved / g.target) if g.target > 0 else 0.0
            amt = comp.num_field("€", "")
            amt.expand = 2
            goals_body.controls.append(ft.Column([
                ft.Row([ft.Text(g.name, color=t.TEXT, weight=ft.FontWeight.W_500, expand=True),
                        ft.Text(f"{_eur(g.saved)} / {_eur(g.target)}", color=t.MUTED, size=12),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=t.FAT,
                                      on_click=lambda e, gid=g.id: (frepo.delete_goal(conn, gid),
                                                                    render(), page.update()))],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.ProgressBar(value=min(max(r, 0), 1), color=t.ACCENT, bgcolor=t.SURFACE_2),
                ft.Row([amt, ft.OutlinedButton(
                    content="Añadir", style=ft.ButtonStyle(color=t.ACCENT),
                    on_click=lambda e, gid=g.id, f=amt: (_num(f.value) > 0 and (
                        frepo.add_to_goal(conn, gid, _num(f.value)), render(), page.update())))],
                    spacing=6)], spacing=6))

    def save_income(e=None):
        frepo.set_income(conn, _num(income_field.value))
        render(); page.update()

    def add_cat(e=None):
        n = (cat_name.value or "").strip()
        if not n:
            return
        frepo.add_category(conn, n, _num(cat_limit.value))
        cat_name.value = cat_limit.value = ""
        render(); page.update()

    def add_exp(e=None):
        a = _num(exp_amount.value)
        if a <= 0:
            return
        cid = int(cat_dd.value) if cat_dd.value else None
        frepo.add_expense(conn, Expense(amount=a, category_id=cid,
                                        note=(exp_note.value or "").strip() or None, on=today))
        exp_amount.value = exp_note.value = ""
        render(); page.update()

    def add_goal(e=None):
        n = (goal_name.value or "").strip()
        if not n:
            return
        frepo.add_goal(conn, n, _num(goal_target.value))
        goal_name.value = goal_target.value = ""
        render(); page.update()

    render()

    income_card = comp.card(ft.Column(
        [comp.label("Nómina"), income_field, comp.secondary_button("Guardar nómina", save_income)],
        spacing=10))
    resumen_card = comp.card(ft.Column([comp.label(f"Resumen · {MONTHS[month]} {year}"), resumen_body], spacing=10))
    cats_card = comp.card(ft.Column(
        [comp.label("Presupuestos"), cats_body, cat_name, cat_limit,
         comp.secondary_button("+ Categoría", add_cat)], spacing=10))
    exp_card = comp.card(ft.Column(
        [comp.label("Gasto rápido"), exp_amount, cat_dd, exp_note,
         comp.primary_button("Añadir gasto", add_exp), exp_list], spacing=10))
    goals_card = comp.card(ft.Column(
        [comp.label("Metas de ahorro"), goals_body, goal_name, goal_target,
         comp.secondary_button("+ Meta", add_goal)], spacing=10))

    return ft.Container(
        bgcolor=t.BG, expand=True, padding=16,
        content=ft.Column(
            [ft.Row([ft.Text("Dinero", size=26, weight=ft.FontWeight.BOLD, color=t.TEXT),
                     ft.Text(f"{MONTHS[month]} {year}", color=t.MUTED)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
             income_card, resumen_card, cats_card, exp_card, goals_card],
            scroll=ft.ScrollMode.AUTO, spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
