"""Pantalla de Registrar: rápido, buscar, código de barras (manual + foto), propios."""

from __future__ import annotations

import flet as ft

from kcn.core.calculations import default_meal_names
from kcn.core.models import Food, FoodEntry
from kcn.data import repository as repo
from kcn.services import openfoodfacts as off
from kcn.ui import components as comp
from kcn.ui import theme as t


def _num(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _persist(conn, food: Food) -> Food:
    if food.id is not None:
        return food
    if food.barcode:
        return repo.upsert_food_by_barcode(conn, food)
    return repo.add_food(conn, food)


def _decode_barcode(data: bytes) -> str | None:
    """Decodifica un código de barras de una imagen (bytes). None si no hay."""
    import io
    import zxingcpp
    from PIL import Image
    img = Image.open(io.BytesIO(data))
    results = zxingcpp.read_barcodes(img)
    return results[0].text if results else None


def build_registrar(state, page: ft.Page) -> ft.Control:
    conn = state.conn
    prof = repo.get_profile(conn)
    if prof is None:
        return ft.Container(
            bgcolor=t.BG, expand=True, padding=16,
            content=comp.card(ft.Text("Crea tu perfil primero (pestaña Perfil).", color=t.MUTED)))

    meal_names = default_meal_names(prof.meal_count)
    selected = {"food": None}

    # --- Panel de registro ---
    add_title = ft.Text("", color=t.TEXT, weight=ft.FontWeight.BOLD, size=16)
    grams = comp.num_field("Cantidad (g)", "")
    meal_dd = ft.Dropdown(
        label="Comida", value="0", filled=True, bgcolor=t.SURFACE_2,
        options=[ft.DropdownOption(key=str(i), text=n) for i, n in enumerate(meal_names)])
    fav_switch = ft.Switch(label="Favorito", value=False, active_color=t.ACCENT)
    add_status = ft.Text("", size=13)

    def select_food(food: Food) -> None:
        selected["food"] = food
        add_title.value = food.name + (f" · {food.brand}" if food.brand else "")
        grams.value = str(int(food.default_serving_g)) if food.default_serving_g else "100"
        fav_switch.value = bool(food.favorite)
        add_status.value = ""
        add_card.visible = True
        page.update()

    def register(e=None) -> None:
        food = selected["food"]
        if food is None:
            return
        g = _num(grams.value, 0)
        if g <= 0:
            add_status.value, add_status.color = "Pon una cantidad válida.", t.FAT
            page.update()
            return
        food = _persist(conn, food)
        if fav_switch.value:
            repo.set_favorite(conn, food.id, True)
        repo.add_entry(conn, FoodEntry(food=food, grams=g, meal_index=int(meal_dd.value)))
        add_status.value = f"Registrado ✓  {food.name} ({int(g)} g)"
        add_status.color = t.ACCENT
        refresh_quick()
        page.update()

    add_card = comp.card(ft.Column(
        [comp.label("Registrar"), add_title, grams, meal_dd, fav_switch,
         comp.primary_button("Añadir al día", register), add_status], spacing=10))
    add_card.visible = False

    # --- Rápido: recientes y favoritos ---
    quick_holder = ft.Column(spacing=8)

    def refresh_quick() -> None:
        quick_holder.controls.clear()
        favs = repo.list_favorites(conn)
        recents = repo.recent_foods(conn, limit=8)
        if favs:
            quick_holder.controls.append(comp.label("★ Favoritos"))
            for f in favs:
                quick_holder.controls.append(comp.list_item(
                    f.name, f"{f.kcal_per_100g:g} kcal/100g", lambda e, ff=f: select_food(ff)))
        if recents:
            quick_holder.controls.append(comp.label("Recientes"))
            for f in recents:
                quick_holder.controls.append(comp.list_item(
                    f.name, f"{f.kcal_per_100g:g} kcal/100g", lambda e, ff=f: select_food(ff)))
        if not favs and not recents:
            quick_holder.controls.append(
                ft.Text("Aquí aparecerán tus alimentos frecuentes y favoritos.", color=t.MUTED))

    refresh_quick()
    quick_card = comp.card(ft.Column([comp.label("Rápido"), quick_holder], spacing=10))

    # --- Buscar por nombre ---
    q_field = comp.num_field("Buscar alimento", "")
    results = ft.Column(spacing=8)

    def do_search(e=None) -> None:
        results.controls.clear()
        q = (q_field.value or "").strip()
        if not q:
            page.update()
            return
        for f in repo.search_foods(conn, q, limit=10):
            results.controls.append(comp.list_item(
                f.name, f"{f.kcal_per_100g:g} kcal/100g · tuyo", lambda e, ff=f: select_food(ff)))
        try:
            for f in off.search(q, limit=10):
                results.controls.append(comp.list_item(
                    f.name + (f" · {f.brand}" if f.brand else ""),
                    f"{f.kcal_per_100g:g} kcal/100g · OFF", lambda e, ff=f: select_food(ff)))
        except Exception as ex:
            results.controls.append(
                ft.Text(f"Sin conexión a Open Food Facts ({ex}).", color=t.MUTED, size=12))
        page.update()

    search_card = comp.card(ft.Column(
        [comp.label("Buscar"), q_field, comp.primary_button("Buscar", do_search), results],
        spacing=10))

    # --- Código de barras: manual + foto ---
    bc_field = comp.num_field("Código de barras", "")
    bc_status = ft.Text("", size=12, color=t.MUTED)

    def lookup_code(code: str) -> None:
        try:
            f = off.get_by_barcode(code)
        except Exception as ex:
            bc_status.value = f"Error de conexión ({ex})."
            page.update()
            return
        if f is None:
            bc_status.value = f"Código {code} no está en Open Food Facts."
            page.update()
        else:
            bc_status.value = ""
            select_food(f)

    def do_barcode(e=None) -> None:
        code = (bc_field.value or "").strip()
        if code:
            lookup_code(code)

    def on_pick(e) -> None:
        if not e.files:
            return
        data = e.files[0].bytes
        if not data:
            bc_status.value = "No se recibió la imagen."
            page.update()
            return
        try:
            code = _decode_barcode(data)
        except Exception as ex:
            bc_status.value = f"No se pudo leer la imagen ({ex})."
            page.update()
            return
        if not code:
            bc_status.value = "No se detectó ningún código en la foto."
            page.update()
            return
        bc_status.value = f"Código {code} detectado, buscando…"
        page.update()
        lookup_code(code)

    # Reutilizamos un único FilePicker en toda la app y actualizamos su handler.
    if getattr(state, "file_picker", None) is None:
        state.file_picker = ft.FilePicker()
        page.services.append(state.file_picker)
    state.file_picker.on_result = on_pick

    scan_btn = ft.Button(
        content="📷 Escanear con la cámara",
        action=ft.PickFiles(state.file_picker, file_type=ft.FilePickerFileType.IMAGE,
                            allow_multiple=False, with_data=True),
        style=ft.ButtonStyle(bgcolor=t.ACCENT, color=t.BG))

    barcode_card = comp.card(ft.Column(
        [comp.label("Código de barras"), bc_field,
         comp.secondary_button("Buscar código", do_barcode),
         scan_btn, bc_status], spacing=10))

    # --- Alimento propio ---
    cf_name = comp.num_field("Nombre", "")
    cf_kcal = comp.num_field("kcal / 100 g", "")
    cf_p = comp.num_field("Proteína / 100 g", "")
    cf_c = comp.num_field("Carbos / 100 g", "")
    cf_g = comp.num_field("Grasa / 100 g", "")
    cf_serv = comp.num_field("Ración típica (g, opcional)", "")
    cf_status = ft.Text("", size=12)

    def create_custom(e=None) -> None:
        name = (cf_name.value or "").strip()
        if not name:
            cf_status.value, cf_status.color = "Ponle un nombre.", t.FAT
            page.update()
            return
        food = Food(name=name, kcal_per_100g=_num(cf_kcal.value, 0),
                    protein_per_100g=_num(cf_p.value, 0), carbs_per_100g=_num(cf_c.value, 0),
                    fat_per_100g=_num(cf_g.value, 0),
                    default_serving_g=(_num(cf_serv.value, 0) or None))
        food = repo.add_food(conn, food)
        cf_status.value, cf_status.color = "Creado ✓ (elige cantidad arriba)", t.ACCENT
        refresh_quick()
        select_food(food)

    custom_card = comp.card(ft.Column(
        [comp.label("Crear alimento propio"), cf_name, cf_kcal, cf_p, cf_c, cf_g, cf_serv,
         comp.secondary_button("Crear y usar", create_custom), cf_status], spacing=10))

    return ft.Container(
        bgcolor=t.BG, expand=True, padding=16,
        content=ft.Column(
            [ft.Text("Registrar", size=26, weight=ft.FontWeight.BOLD, color=t.TEXT),
             add_card, quick_card, search_card, barcode_card, custom_card],
            scroll=ft.ScrollMode.AUTO, spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
