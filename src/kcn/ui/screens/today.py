"""Dashboard 'Hoy' unificado: comida, agua, entreno, dinero y hábitos."""

from __future__ import annotations

from datetime import date

import flet as ft

from kcn.core.models import WaterEntry
from kcn.data import repository as repo
from kcn.services import day as day_service
from kcn.services import recommender as rec_service
from kcn.fitness import repo as fitrepo
from kcn.finance import repo as finrepo
from kcn.habits import repo as habrepo
from kcn.ui import components as comp
from kcn.ui import theme as t


def _eur(x: float) -> str:
    return f"{x:.0f} €"


def _mealplan_controls(mp) -> list[ft.Control]:
    if mp.recipe is not None:
        m = mp.macros
        return [ft.Text(f"🍽  {mp.recipe.name}  (x{mp.recipe_servings:g})",
                        color=t.TEXT, weight=ft.FontWeight.W_500),
                ft.Text(f"{m.kcal} kcal · P{m.protein_g} C{m.carbs_g} G{m.fat_g}",
                        color=t.MUTED, size=12)]
    if mp.items:
        rows = [ft.Text(f"•  {round(it.grams)} g {it.food.name}", color=t.TEXT) for it in mp.items]
        m = mp.macros
        rows.append(ft.Text(f"{m.kcal} kcal · P{m.protein_g} C{m.carbs_g} G{m.fat_g}",
                            color=t.MUTED, size=12))
        return rows
    return [ft.Text("Sin sugerencia: añade alimentos a tu biblioteca.", color=t.MUTED)]


def build_today(state, page: ft.Page) -> ft.Control:
    conn = state.conn
    prof = repo.get_profile(conn)
    if prof is None:
        return ft.Container(
            bgcolor=t.BG, expand=True, padding=16,
            content=comp.card(ft.Column(
                [ft.Text("Bienvenido a KCN", size=22, weight=ft.FontWeight.BOLD, color=t.TEXT),
                 ft.Text("Crea tu perfil en la pestaña Yo → Perfil para empezar.", color=t.MUTED)],
                spacing=8)))

    data_col = ft.Column(spacing=16)
    rec_body = ft.Column(spacing=6)

    def render() -> None:
        today = date.today()
        summary = day_service.get_day_summary(conn, prof, on=today)
        budget = summary.calorie_budget
        consumed = summary.consumed.kcal
        rem = summary.remaining.kcal
        ratio = (consumed / budget) if budget > 0 else 0.0

        def add_water(ml):
            repo.add_water(conn, WaterEntry(ml=ml))
            render(); page.update()

        def toggle_habit(hid, value):
            habrepo.set_done(conn, hid, today, value)
            render(); page.update()

        # Calorías
        cal_card = comp.card(ft.Column([
            comp.label("Calorías de hoy"),
            ft.Row([ft.Text(str(consumed), size=40, weight=ft.FontWeight.BOLD, color=t.KCAL),
                    ft.Text(f"/ {budget} kcal", size=14, color=t.MUTED)],
                   vertical_alignment=ft.CrossAxisAlignment.END, spacing=8),
            ft.ProgressBar(value=min(max(ratio, 0), 1), color=t.KCAL, bgcolor=t.SURFACE_2),
            ft.Text(f"Restan {rem} kcal", color=(t.ACCENT if rem >= 0 else t.FAT),
                    weight=ft.FontWeight.W_500),
            comp.macro_bar("Proteína", summary.consumed.protein_g, summary.target.protein_g, t.PROTEIN),
            comp.macro_bar("Carbos", summary.consumed.carbs_g, summary.target.carbs_g, t.CARB),
            comp.macro_bar("Grasa", summary.consumed.fat_g, summary.target.fat_g, t.FAT)],
            spacing=10))

        # Entreno + Dinero (tiles)
        income = finrepo.get_income(conn)
        spent = finrepo.month_spent(conn, today.year, today.month)
        avail = income - spent
        n_sessions = len(fitrepo.get_sessions_for_date(conn, today))
        tiles = ft.Row([
            comp.stat_tile("Entreno hoy", f"{summary.exercise_kcal} kcal", t.ACCENT),
            comp.stat_tile("Disponible (mes)", _eur(avail), t.ACCENT if avail >= 0 else t.FAT)],
            spacing=10)

        # Agua
        wr = (summary.water_ml / summary.water_goal_ml) if summary.water_goal_ml > 0 else 0.0

        def wbtn(ml):
            return ft.OutlinedButton(content=f"+{ml}", on_click=lambda e: add_water(ml),
                                     expand=True, style=ft.ButtonStyle(color=t.CARB))

        water_card = comp.card(ft.Column([
            comp.label("Agua"),
            ft.Row([ft.Text(f"{summary.water_ml} / {summary.water_goal_ml} ml",
                            color=t.TEXT, weight=ft.FontWeight.W_500),
                    ft.Text(f"{int(min(wr,1)*100)}%", color=t.MUTED)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.ProgressBar(value=min(max(wr, 0), 1), color=t.CARB, bgcolor=t.SURFACE_2),
            ft.Row([wbtn(250), wbtn(500), wbtn(750)], spacing=8)], spacing=10))

        # Hábitos
        hab_col = ft.Column(spacing=6)
        habits = habrepo.list_habits(conn)
        done_ids = habrepo.done_ids_for_date(conn, today)
        if not habits:
            hab_col.controls.append(ft.Text("Crea hábitos en Yo → Hábitos.", color=t.MUTED))
        for h in habits:
            hab_col.controls.append(ft.Row([
                ft.Checkbox(value=(h.id in done_ids),
                            on_change=lambda e, hid=h.id: toggle_habit(hid, e.control.value)),
                ft.Text(h.name, color=t.TEXT, expand=True),
                ft.Text(f"🔥 {habrepo.streak(conn, h.id, today)}",
                        color=t.MUTED, size=12)],
                vertical_alignment=ft.CrossAxisAlignment.CENTER))
        hab_card = comp.card(ft.Column([comp.label("Hábitos de hoy"), hab_col], spacing=10))

        data_col.controls.clear()
        data_col.controls.extend([
            ft.Row([ft.Text("Hoy", size=26, weight=ft.FontWeight.BOLD, color=t.TEXT),
                    ft.Text(today.strftime("%d/%m/%Y"), color=t.MUTED)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            cal_card, tiles, water_card, hab_card])

    def on_plan(e=None) -> None:
        rec_body.controls.clear()
        for name, mp in rec_service.plan_today(conn, prof):
            rec_body.controls.append(comp.label(name))
            rec_body.controls.extend(_mealplan_controls(mp))
            rec_body.controls.append(ft.Divider(color=t.BORDER))
        page.update()

    def on_next(e=None) -> None:
        rec_body.controls.clear()
        meal, mp = rec_service.next_meal_idea(conn, prof)
        rec_body.controls.append(comp.label(f"Idea para {meal.name}"))
        rec_body.controls.extend(_mealplan_controls(mp))
        page.update()

    rec_card = comp.card(ft.Column([
        comp.label("Recomendación de comida"),
        comp.primary_button("Plan de comida para hoy", on_plan),
        comp.secondary_button("Idea siguiente comida", on_next),
        rec_body], spacing=10))

    render()

    return ft.Container(
        bgcolor=t.BG, expand=True, padding=16,
        content=ft.Column([data_col, rec_card], scroll=ft.ScrollMode.AUTO, spacing=16,
                          horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
