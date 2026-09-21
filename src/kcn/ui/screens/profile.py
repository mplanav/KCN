"""Pantalla de Perfil: crea/edita tu perfil y muestra tus objetivos."""

from __future__ import annotations

import flet as ft

from kcn.core.calculations import (
    default_meal_names, default_meal_weights, macro_targets, split_into_meals,
)
from kcn.core.models import ActivityLevel, Goal, Sex, UserProfile
from kcn.data import repository as repo
from kcn.ui import components as comp
from kcn.ui import theme as t

SEX_TEXT = {Sex.MALE: "Hombre", Sex.FEMALE: "Mujer"}


def _num(value: str, default: float) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def build_profile(state, page: ft.Page) -> ft.Control:
    conn = state.conn
    p = repo.get_profile(conn)

    weight = comp.num_field("Peso (kg)", str(p.weight_kg) if p else "")
    height = comp.num_field("Altura (cm)", str(p.height_cm) if p else "")
    age = comp.num_field("Edad", str(p.age) if p else "")
    sex = ft.Dropdown(label="Sexo", value=(p.sex.name if p else Sex.MALE.name),
                      filled=True, border_radius=12, bgcolor=t.SURFACE_2,
                      options=[ft.DropdownOption(key=s.name, text=SEX_TEXT[s]) for s in Sex])
    activity = ft.Dropdown(label="Actividad",
                           value=(p.activity.name if p else ActivityLevel.VERY_ACTIVE.name),
                           filled=True, border_radius=12, bgcolor=t.SURFACE_2,
                           options=[ft.DropdownOption(key=a.name, text=a.label) for a in ActivityLevel])
    goal = ft.Dropdown(label="Objetivo", value=(p.goal.name if p else Goal.MAINTAIN.name),
                       filled=True, border_radius=12, bgcolor=t.SURFACE_2,
                       options=[ft.DropdownOption(key=g.name, text=g.label) for g in Goal])
    weekly = comp.num_field("Ritmo (kg/semana)", str(p.weekly_rate_kg) if p else "0.5")
    meals = comp.num_field("Comidas al día", str(p.meal_count) if p else "5")
    protein = comp.num_field("Proteína (g/kg)", str(p.protein_per_kg) if p else "1.8")
    fat = comp.num_field("Grasa (g/kg)", str(p.fat_per_kg) if p else "0.9")

    status = ft.Text("", size=13)
    obj_body = ft.Column(spacing=12)

    def render_targets() -> None:
        obj_body.controls.clear()
        prof = repo.get_profile(conn)
        if prof is None:
            obj_body.controls.append(
                ft.Text("Guarda tu perfil para ver tus objetivos.", color=t.MUTED))
            return
        tt = macro_targets(prof)
        obj_body.controls.append(ft.Row(
            [ft.Text(str(tt.kcal), size=40, weight=ft.FontWeight.BOLD, color=t.KCAL),
             ft.Text("kcal / día", size=14, color=t.MUTED)],
            vertical_alignment=ft.CrossAxisAlignment.END, spacing=8))
        obj_body.controls.append(ft.Row(
            [comp.stat_tile("Proteína", f"{tt.protein_g} g", t.PROTEIN),
             comp.stat_tile("Carbos", f"{tt.carbs_g} g", t.CARB),
             comp.stat_tile("Grasa", f"{tt.fat_g} g", t.FAT)],
            spacing=10))
        obj_body.controls.append(ft.Divider(color=t.BORDER))
        obj_body.controls.append(comp.label("Reparto por comidas"))
        for m in split_into_meals(tt, weights=default_meal_weights(prof.meal_count),
                                  names=default_meal_names(prof.meal_count)):
            x = m.targets
            obj_body.controls.append(ft.Row(
                [ft.Text(m.name, color=t.TEXT, weight=ft.FontWeight.W_500),
                 ft.Text(f"{x.kcal} kcal · P{x.protein_g} C{x.carbs_g} G{x.fat_g}", color=t.MUTED)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

    def save(e=None) -> None:
        try:
            prof = UserProfile(
                weight_kg=_num(weight.value, 0), height_cm=_num(height.value, 0),
                age=int(_num(age.value, 0)), sex=Sex[sex.value],
                activity=ActivityLevel[activity.value], goal=Goal[goal.value],
                weekly_rate_kg=_num(weekly.value, 0.5), meal_count=int(_num(meals.value, 5)),
                protein_per_kg=_num(protein.value, 1.8), fat_per_kg=_num(fat.value, 0.9))
        except (ValueError, KeyError) as ex:
            status.value, status.color = f"Revisa los datos: {ex}", t.FAT
            page.update()
            return
        repo.save_profile(conn, prof)
        status.value, status.color = "Perfil guardado ✓", t.ACCENT
        render_targets()
        page.update()

    render_targets()

    form = comp.card(ft.Column(
        [comp.label("Tus datos"), weight, height, age, sex, activity, goal,
         comp.label("Ajustes de macros"), weekly, meals, protein, fat,
         comp.primary_button("Guardar y calcular", save), status],
        spacing=12))

    return ft.Container(
        bgcolor=t.BG, expand=True, padding=16,
        content=ft.Column(
            [ft.Text("Perfil", size=26, weight=ft.FontWeight.BOLD, color=t.TEXT),
             comp.card(obj_body),
             form],
            scroll=ft.ScrollMode.AUTO, spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
    )