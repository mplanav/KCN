"""Pantalla de Hoy: resumen del día, registros por comida, agua y ejercicio."""

from __future__ import annotations

from datetime import date

import flet as ft

from kcn.core.models import WaterEntry, Workout
from kcn.data import repository as repo
from kcn.services import day as day_service
from kcn.services import recommender as rec_service
from kcn.ui import components as comp
from kcn.ui import theme as t


def _num(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


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
                 ft.Text("Crea tu perfil en la pestaña Perfil para empezar.", color=t.MUTED)],
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

        def del_entry(eid):
            repo.delete_entry(conn, eid)
            render()
            page.update()

        def add_water(ml):
            repo.add_water(conn, WaterEntry(ml=ml))
            render()
            page.update()

        hero = comp.card(ft.Column([
            comp.label("Calorías de hoy"),
            ft.Row([ft.Text(str(consumed), size=42, weight=ft.FontWeight.BOLD, color=t.KCAL),
                    ft.Text(f"/ {budget} kcal", size=14, color=t.MUTED)],
                   vertical_alignment=ft.CrossAxisAlignment.END, spacing=8),
            ft.ProgressBar(value=min(max(ratio, 0), 1), color=t.KCAL, bgcolor=t.SURFACE_2),
            ft.Row([ft.Text(f"Restan {rem} kcal", color=(t.ACCENT if rem >= 0 else t.FAT),
                            weight=ft.FontWeight.W_500),
                    ft.Text(f"Objetivo {summary.target.kcal} · Ejercicio +{summary.exercise_kcal}",
                            color=t.MUTED, size=12)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN)], spacing=10))

        macros = comp.card(ft.Column([
            comp.label("Macros"),
            comp.macro_bar("Proteína", summary.consumed.protein_g, summary.target.protein_g, t.PROTEIN),
            comp.macro_bar("Carbos", summary.consumed.carbs_g, summary.target.carbs_g, t.CARB),
            comp.macro_bar("Grasa", summary.consumed.fat_g, summary.target.fat_g, t.FAT)],
            spacing=12))

        meals_col = ft.Column(spacing=14)
        for m in summary.meals:
            r = (m.consumed.kcal / m.target.kcal) if m.target.kcal > 0 else 0.0
            rows = [ft.Row([ft.Text(m.name, color=t.TEXT, weight=ft.FontWeight.W_500),
                            ft.Text(f"{m.consumed.kcal} / {m.target.kcal} kcal", color=t.MUTED, size=12)],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.ProgressBar(value=min(max(r, 0), 1), color=t.KCAL, bgcolor=t.SURFACE_2)]
            for entry in m.entries:
                em = entry.macros
                rows.append(ft.Row([
                    ft.Text(f"{round(entry.grams)} g {entry.food.name}", color=t.MUTED, size=12, expand=True),
                    ft.Text(f"{em.kcal} kcal", color=t.MUTED, size=12),
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=t.FAT,
                                  on_click=lambda e, eid=entry.id: del_entry(eid))],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER))
            meals_col.controls.append(ft.Column(rows, spacing=4))
        meals_card = comp.card(ft.Column([comp.label("Comidas"), meals_col], spacing=12))

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

        ex_desc = comp.num_field("Entreno (p. ej. Natación 30 min)", "")
        ex_kcal = comp.num_field("kcal quemadas", "")
        ex_dur = comp.num_field("Minutos (opcional)", "")
        ex_status = ft.Text("", size=12)

        def add_ex(e=None):
            d = (ex_desc.value or "").strip()
            k = int(_num(ex_kcal.value, 0))
            if not d or k <= 0:
                ex_status.value, ex_status.color = "Pon descripción y kcal.", t.FAT
                page.update()
                return
            dur = _num(ex_dur.value, 0)
            repo.add_workout(conn, Workout(description=d, calories=k,
                                           duration_min=int(dur) if dur > 0 else None))
            render()
            page.update()

        ex_list = ft.Column(spacing=2)
        for wk in repo.get_workouts_for_date(conn, today):
            ex_list.controls.append(ft.Row([
                ft.Text(f"{wk.description} — {wk.calories} kcal", color=t.MUTED, size=12, expand=True),
                ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=t.FAT,
                              on_click=lambda e, wid=wk.id: (repo.delete_workout(conn, wid), render(), page.update()))],
                vertical_alignment=ft.CrossAxisAlignment.CENTER))

        exercise_card = comp.card(ft.Column([
            comp.label("Ejercicio"),
            ft.Text(f"{summary.exercise_kcal} kcal quemadas hoy", color=t.TEXT, weight=ft.FontWeight.W_500),
            ex_list, ex_desc, ex_kcal, ex_dur,
            comp.secondary_button("Añadir entreno", add_ex), ex_status], spacing=10))

        data_col.controls.clear()
        data_col.controls.extend([
            ft.Row([ft.Text("Hoy", size=26, weight=ft.FontWeight.BOLD, color=t.TEXT),
                    ft.Text(today.strftime("%d/%m/%Y"), color=t.MUTED)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            hero, macros, meals_card, water_card, exercise_card])

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
        comp.label("Recomendación"),
        comp.primary_button("Plan de comida para hoy", on_plan),
        comp.secondary_button("Idea siguiente comida", on_next),
        rec_body], spacing=10))

    render()

    return ft.Container(
        bgcolor=t.BG, expand=True, padding=16,
        content=ft.Column([data_col, rec_card], scroll=ft.ScrollMode.AUTO, spacing=16,
                          horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
