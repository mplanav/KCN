"""Pantalla de Entreno: registrar sesiones con series + historial del día."""

from __future__ import annotations

from datetime import date

import flet as ft

from kcn.fitness import repo as frepo
from kcn.fitness.models import Exercise, ExerciseSet, WorkoutSession
from kcn.ui import components as comp
from kcn.ui import theme as t


def _num(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def build_entreno(state, page: ft.Page) -> ft.Control:
    conn = state.conn
    today = date.today()

    name = comp.num_field("Nombre (Push, Piernas, Natación…)", "")
    kcal = comp.num_field("kcal quemadas (opcional)", "")
    dur = comp.num_field("Minutos (opcional)", "")
    note = comp.num_field("Nota (opcional)", "")
    status = ft.Text("", size=13)

    sets_col = ft.Column(spacing=8)
    set_rows: list[dict] = []

    def rebuild_sets() -> None:
        sets_col.controls.clear()
        for rr in set_rows:
            sets_col.controls.append(ft.Row(
                [rr["ex"], rr["w"], rr["r"],
                 ft.IconButton(ft.Icons.CLOSE, icon_size=18, icon_color=t.FAT,
                               on_click=rr["remove"])],
                spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER))

    def add_set_row(e=None) -> None:
        ex = comp.num_field("Ejercicio", ""); ex.expand = 3
        w = comp.num_field("kg", ""); w.expand = 2
        r = comp.num_field("reps", ""); r.expand = 2
        rr = {"ex": ex, "w": w, "r": r}
        rr["remove"] = lambda e, ref=rr: (set_rows.remove(ref), rebuild_sets(), page.update())
        set_rows.append(rr)
        rebuild_sets()

    sess_col = ft.Column(spacing=12)

    def refresh_sessions() -> None:
        sess_col.controls.clear()
        sessions = frepo.get_sessions_for_date(conn, today)
        if not sessions:
            sess_col.controls.append(ft.Text("Sin entrenos hoy.", color=t.MUTED))
            return
        for s in sessions:
            lines = [ft.Row(
                [ft.Text(s.name, color=t.TEXT, weight=ft.FontWeight.W_500),
                 ft.Row([ft.Text(f"{s.calories or 0} kcal · vol {int(s.volume)}", color=t.MUTED, size=12),
                         ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, icon_color=t.FAT,
                                       on_click=lambda e, sid=s.id: (frepo.delete_session(conn, sid),
                                                                     refresh_sessions(), page.update()))],
                        spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN)]
            for st in s.sets:
                w = f"{st.weight_kg:g} kg" if st.weight_kg else ""
                reps = f"x{st.reps}" if st.reps else ""
                txt = f"  • {st.exercise.name}  {w} {reps}".rstrip()
                lines.append(ft.Text(txt, color=t.MUTED, size=12))
            sess_col.controls.append(ft.Container(
                bgcolor=t.SURFACE_2, border_radius=12, padding=12,
                content=ft.Column(lines, spacing=4)))

    def save(e=None) -> None:
        n = (name.value or "").strip()
        sets = []
        for rr in set_rows:
            exn = (rr["ex"].value or "").strip()
            if not exn:
                continue
            wv = _num(rr["w"].value)
            rv = _num(rr["r"].value)
            sets.append(ExerciseSet(Exercise(exn), weight_kg=(wv or None), reps=(int(rv) or None)))
        if not n and not sets:
            status.value, status.color = "Pon un nombre o alguna serie.", t.FAT
            page.update()
            return
        frepo.add_session(conn, WorkoutSession(
            name=n or "Entreno", on=today,
            calories=int(_num(kcal.value)) or None,
            duration_min=int(_num(dur.value)) or None,
            note=(note.value or "").strip() or None, sets=sets))
        name.value = kcal.value = dur.value = note.value = ""
        set_rows.clear()
        add_set_row()
        status.value, status.color = "Sesión guardada ✓", t.ACCENT
        refresh_sessions()
        page.update()

    add_set_row()
    refresh_sessions()

    register_card = comp.card(ft.Column([
        comp.label("Registrar sesión"), name, kcal, dur, note,
        comp.label("Series"), sets_col,
        comp.secondary_button("+ Añadir serie", add_set_row),
        comp.primary_button("Guardar sesión", save), status], spacing=10))

    sessions_card = comp.card(ft.Column([comp.label("Entrenos de hoy"), sess_col], spacing=10))

    return ft.Container(
        bgcolor=t.BG, expand=True, padding=16,
        content=ft.Column(
            [ft.Row([ft.Text("Entreno", size=26, weight=ft.FontWeight.BOLD, color=t.TEXT),
                     ft.Text(today.strftime("%d/%m/%Y"), color=t.MUTED)],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
             register_card, sessions_card],
            scroll=ft.ScrollMode.AUTO, spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
