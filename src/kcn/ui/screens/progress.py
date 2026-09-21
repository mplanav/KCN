"""Pantalla de Progreso: medidas, IMC, adherencia, ajuste y gráfica de evolución."""

from __future__ import annotations

import flet as ft

from kcn.core.calculations import bmi, bmi_category
from kcn.core.models import BodyMeasurement
from kcn.data import repository as repo
from kcn.services import adherence as adh_service
from kcn.services import progress as progress_service
from kcn.ui import charts
from kcn.ui import components as comp
from kcn.ui import theme as t

METRICS = [
    ("weight", "Peso", "kg", t.KCAL),
    ("body_fat", "% Grasa", "%", t.FAT),
    ("water", "% Agua", "%", t.CARB),
    ("muscle", "Músculo", "kg", t.PROTEIN),
    ("bone", "Hueso", "kg", t.MUTED),
    ("visceral", "Visceral", "", t.ACCENT),
]


def _optnum(value):
    v = (str(value) if value is not None else "").strip()
    if not v:
        return None
    try:
        return float(v.replace(",", "."))
    except ValueError:
        return None


def build_progress(state, page: ft.Page) -> ft.Control:
    conn = state.conn
    prof = repo.get_profile(conn)
    if prof is None:
        return ft.Container(
            bgcolor=t.BG, expand=True, padding=16,
            content=comp.card(ft.Text("Crea tu perfil primero (pestaña Perfil).", color=t.MUTED)))

    state_col = ft.Column(spacing=16)

    def refresh() -> None:
        state_col.controls.clear()
        latest = repo.latest_measurement(conn)

        body: list[ft.Control] = [comp.label("Estado actual")]
        weight_val = latest.weight_kg if (latest and latest.weight_kg) else prof.weight_kg
        if weight_val:
            b = bmi(weight_val, prof.height_cm)
            body.append(ft.Row(
                [ft.Text(f"{weight_val:g} kg", size=28, weight=ft.FontWeight.BOLD, color=t.TEXT),
                 ft.Text(f"IMC {b:.1f} · {bmi_category(b)}", color=t.MUTED)],
                vertical_alignment=ft.CrossAxisAlignment.END, spacing=10))
        if latest:
            chips: list[ft.Control] = []
            pairs = [("Grasa", latest.body_fat_pct, "%"), ("Agua", latest.water_pct, "%"),
                     ("Músculo", latest.muscle_mass_kg, " kg"), ("Hueso", latest.bone_mass_kg, " kg"),
                     ("Visceral", latest.visceral_fat, "")]
            for lbl, val, unit in pairs:
                if val is not None:
                    chips.append(ft.Text(f"{lbl}: {val:g}{unit}", color=t.MUTED, size=12))
            if latest.metabolic_age is not None:
                chips.append(ft.Text(f"Edad metabólica: {latest.metabolic_age}", color=t.MUTED, size=12))
            if chips:
                body.append(ft.Column(chips, spacing=2))
        else:
            body.append(ft.Text("Aún no has registrado medidas.", color=t.MUTED))
        state_col.controls.append(comp.card(ft.Column(body, spacing=10)))

        rate = adh_service.adherence_rate(conn, prof, days=30)
        streak = adh_service.current_streak(conn, prof, max_lookback=60)
        state_col.controls.append(comp.card(ft.Column(
            [comp.label("Adherencia (30 días)"),
             ft.Row([ft.Text(f"{int(rate * 100)}%", size=24, weight=ft.FontWeight.BOLD, color=t.ACCENT),
                     ft.Text(f"Racha: {streak} días", color=t.MUTED)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
             ft.ProgressBar(value=min(max(rate, 0), 1), color=t.ACCENT, bgcolor=t.SURFACE_2)],
            spacing=10)))

        adj = progress_service.adjustment(conn, prof)
        aj: list[ft.Control] = [comp.label("Ajuste por progreso")]
        if not adj.enough_data:
            aj.append(ft.Text(adj.reason, color=t.MUTED))
        elif adj.on_track:
            aj.append(ft.Text(adj.reason, color=t.ACCENT))
        else:
            aj.append(ft.Text(adj.reason, color=t.TEXT))
            aj.append(ft.Text(f"Sugerido: {adj.suggested_kcal} kcal/día",
                              color=t.ACCENT, weight=ft.FontWeight.W_500))
        state_col.controls.append(comp.card(ft.Column(aj, spacing=8)))

    metric_dd = ft.Dropdown(
        value="weight", filled=True, bgcolor=t.SURFACE_2,
        options=[ft.DropdownOption(key=k, text=lbl) for k, lbl, _, _ in METRICS])
    chart_holder = ft.Column(spacing=8)

    def render_chart(e=None) -> None:
        key = metric_dd.value
        _, _, unit, color = next(m for m in METRICS if m[0] == key)
        series = repo.measurement_series(conn, key)
        chart_holder.controls.clear()
        if len(series) < 2:
            chart_holder.controls.append(
                ft.Text("Registra al menos 2 valores para ver la evolución.", color=t.MUTED))
            page.update()
            return
        b64 = charts.line_png_b64(series, color)
        chart_holder.controls.append(
            ft.Image(src=f"data:image/png;base64,{b64}", height=220))
        ys = [v for _, v in series]
        chart_holder.controls.append(
            ft.Text(f"Último: {ys[-1]:g}{unit}  ·  Cambio total: {ys[-1] - ys[0]:+.1f}{unit}",
                    color=t.MUTED, size=12))
        page.update()

    metric_dd.on_select = render_chart
    chart_card = comp.card(ft.Column([comp.label("Evolución"), metric_dd, chart_holder], spacing=10))

    w = comp.num_field("Peso (kg)", "")
    bf = comp.num_field("Grasa corporal (%)", "")
    wat = comp.num_field("Agua (%)", "")
    mm = comp.num_field("Masa muscular (kg)", "")
    bm = comp.num_field("Masa ósea (kg)", "")
    vf = comp.num_field("Grasa visceral", "")
    ma = comp.num_field("Edad metabólica", "")
    m_status = ft.Text("", size=13)

    def save(e=None) -> None:
        ma_val = _optnum(ma.value)
        m = BodyMeasurement(
            weight_kg=_optnum(w.value), body_fat_pct=_optnum(bf.value),
            water_pct=_optnum(wat.value), muscle_mass_kg=_optnum(mm.value),
            bone_mass_kg=_optnum(bm.value), visceral_fat=_optnum(vf.value),
            metabolic_age=int(ma_val) if ma_val is not None else None)
        if all(getattr(m, f) is None for f in
               ("weight_kg", "body_fat_pct", "water_pct", "muscle_mass_kg",
                "bone_mass_kg", "visceral_fat", "metabolic_age")):
            m_status.value, m_status.color = "Pon al menos un valor.", t.FAT
            page.update()
            return
        repo.add_measurement(conn, m)
        for field in (w, bf, wat, mm, bm, vf, ma):
            field.value = ""
        m_status.value, m_status.color = "Medida guardada ✓", t.ACCENT
        refresh()
        render_chart()
        page.update()

    measure_card = comp.card(ft.Column(
        [comp.label("Registrar medidas (todo opcional)"),
         w, bf, wat, mm, bm, vf, ma,
         comp.primary_button("Guardar medida", save), m_status], spacing=10))

    refresh()
    render_chart()

    return ft.Container(
        bgcolor=t.BG, expand=True, padding=16,
        content=ft.Column(
            [ft.Text("Progreso", size=26, weight=ft.FontWeight.BOLD, color=t.TEXT),
             state_col, chart_card, measure_card],
            scroll=ft.ScrollMode.AUTO, spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
