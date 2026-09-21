"""Sistema de diseño de KCN: colores, espaciado y tema."""

import flet as ft

# Fondo y superficies (tema oscuro)
BG = "#0E1116"
SURFACE = "#171C25"
SURFACE_2 = "#212A38"
BORDER = "#2A3341"

# Texto
TEXT = "#F2F5F8"
MUTED = "#8A96A6"

# Acento y macros
ACCENT = "#B9F227"     # lima
KCAL = "#B9F227"
PROTEIN = "#FFB020"    # ámbar
CARB = "#4FC3F7"       # azul
FAT = "#FF7A85"        # rojo suave

# Escala de espaciado / radios
SP = 16
RADIUS = 18


def app_theme() -> ft.Theme:
    return ft.Theme(color_scheme_seed=ACCENT)