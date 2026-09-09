"""Cliente de Open Food Facts: buscar alimentos por nombre y por código de barras.

Fuente de datos: Open Food Facts (base colaborativa, abierta). Ver FUENTES.md #8.

Búsqueda por texto: OFF no expone los nutrientes en su buscador (Search-a-licious),
así que lo usamos solo para obtener los códigos y luego "hidratamos" cada producto
con el endpoint de producto v2 (una única llamada por lotes con ?code=...).
"""

from __future__ import annotations

import httpx

from kcn import __version__
from kcn.core.models import Food, FoodSource

# Endpoints oficiales.
V2_PRODUCT = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
V2_SEARCH = "https://world.openfoodfacts.org/api/v2/search"          # productos por código (lote)
TEXT_SEARCH = "https://search.openfoodfacts.org/search"             # búsqueda de texto (solo códigos)

# Campos que necesitamos del producto (respuestas más ligeras).
FIELDS = "code,product_name,generic_name,brands,nutriments,serving_quantity"

# OFF pide que las apps se identifiquen. Ver FUENTES.md #8.
HEADERS = {"User-Agent": f"KCN/{__version__} (open-source nutrition app)"}

DEFAULT_TIMEOUT = 10.0


def _num(value, default: float = 0.0) -> float:
    """Convierte a float de forma segura (OFF a veces manda números como texto)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_product(product: dict) -> Food | None:
    """Convierte un producto de Open Food Facts en un `Food`.

    Devuelve None si no hay datos mínimos usables (nombre y energía).
    """
    name = (product.get("product_name") or product.get("generic_name") or "").strip()
    if not name:
        return None

    nutr = product.get("nutriments", {}) or {}

    kcal = nutr.get("energy-kcal_100g")
    if kcal is None:
        kj = nutr.get("energy_100g") or nutr.get("energy-kj_100g")
        kcal = _num(kj) / 4.184 if kj is not None else None
    if kcal is None:
        return None

    brand = (product.get("brands") or "").split(",")[0].strip() or None
    serving = product.get("serving_quantity")

    return Food(
        name=name,
        brand=brand,
        barcode=str(product.get("code")) if product.get("code") else None,
        source=FoodSource.OPEN_FOOD_FACTS,
        kcal_per_100g=round(_num(kcal), 1),
        protein_per_100g=round(_num(nutr.get("proteins_100g")), 1),
        carbs_per_100g=round(_num(nutr.get("carbohydrates_100g")), 1),
        fat_per_100g=round(_num(nutr.get("fat_100g")), 1),
        default_serving_g=_num(serving) or None,
    )


def get_by_barcode(barcode: str, timeout: float = DEFAULT_TIMEOUT) -> Food | None:
    """Busca un producto por su código de barras. None si no existe o no es usable."""
    resp = httpx.get(V2_PRODUCT.format(barcode=barcode), params={"fields": FIELDS},
                     headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    product = resp.json().get("product")
    return _parse_product(product) if product else None


def _hydrate_codes(codes: list[str], timeout: float) -> dict[str, Food]:
    """Trae los productos completos (con nutrientes) de varios códigos en una llamada."""
    if not codes:
        return {}
    resp = httpx.get(V2_SEARCH, params={"code": ",".join(codes), "fields": FIELDS},
                     headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    result: dict[str, Food] = {}
    for p in resp.json().get("products", []):
        food = _parse_product(p)
        if food and food.barcode:
            result[food.barcode] = food
    return result


def search(query: str, limit: int = 15, timeout: float = DEFAULT_TIMEOUT) -> list[Food]:
    """Busca alimentos por nombre. Devuelve `Food` completos, en orden de relevancia."""
    resp = httpx.get(TEXT_SEARCH,
                     params={"q": query, "page_size": limit, "fields": "code,product_name"},
                     headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    codes = [str(h["code"]) for h in hits if h.get("code")]

    by_code = _hydrate_codes(codes, timeout)

    # Respetar el orden de relevancia del buscador; saltar los que no se pudieron hidratar.
    return [by_code[c] for c in codes if c in by_code]