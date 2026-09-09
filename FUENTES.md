# FUENTES — Base científica de KCN

Regla del proyecto: **ningún valor que afecte a decisiones de salud se usa sin
una fuente oficial documentada aquí.** Cada constante en el código lleva una
etiqueta `[#N]` que remite a esta lista.

## #1 — Ecuación del metabolismo basal (BMR): Mifflin-St Jeor
- **Fórmula:** H: 10·peso + 6.25·altura − 5·edad + 5 · M: −161 en vez de +5.
- **Origen:** Mifflin MD, St Jeor ST, et al. *A new predictive equation for
  resting energy expenditure in healthy individuals.* Am J Clin Nutr, 1990.
- **Respaldo:** La **Academy of Nutrition and Dietetics** la recomienda como la
  ecuación más precisa cuando no hay calorimetría indirecta (valoración
  "Strong"). https://www.andeal.org/template.cfm?template=guide_summary&key=621
- **Nota:** Validada sobre todo en población caucásica; la calorimetría directa
  sigue siendo el patrón oro. Futuro: si el usuario aporta % de grasa corporal,
  ofrecer **Katch-McArdle** (basada en masa magra).

## #2 — Factores de actividad (PAL): FAO/WHO/UNU
- **Valores usados:** 1.40 / 1.55 / 1.70 / 1.85 / 2.10.
- **Bandas oficiales:** sedentario/ligero 1.40–1.69 · activo/moderado 1.70–1.99
  · vigoroso 2.00–2.40 (PAL > 2.40 no sostenible a largo plazo).
- **Fuente:** FAO/WHO/UNU, *Human Energy Requirements* (2004), cap. 5.
  https://www.fao.org/4/y5686e/y5686e07.htm
- **TEE = PAL × BMR.**

## #3 — Proteína: International Society of Sports Nutrition (ISSN)
- **Recomendación:** 1.4–2.0 g/kg/día para construir y mantener masa muscular
  en personas que entrenan; 1.6–2.4 g/kg/día para preservar masa magra en
  déficit calórico combinado con ejercicio.
- **Valores KCN:** 1.8 g/kg por defecto (mantenimiento), 2.0 g/kg en definición.
- **Fuente:** Jäger R, et al. *ISSN Position Stand: protein and exercise.*
  J Int Soc Sports Nutr, 2017. https://doi.org/10.1186/s12970-017-0177-8

## #4 — Distribución de macros (AMDR): Institute of Medicine (IOM/NAM)
- **Rangos (% de energía):** grasa 20–35% · carbohidratos 45–65% ·
  proteína 10–35%.
- **Uso en KCN:** la grasa nunca baja del 20% de las kcal (suelo hormonal).
- **Fuente:** Institute of Medicine, *Dietary Reference Intakes for Energy,
  Carbohydrate, Fiber, Fat, Fatty Acids... Protein and Amino Acids* (2002/2005).
  https://www.ncbi.nlm.nih.gov/books/NBK610333/

## #5 — Energía por gramo: factores de Atwater
- Proteína 4 kcal/g · Carbohidratos 4 kcal/g · Grasa 9 kcal/g.
- Sistema Atwater, estándar internacional (FAO, *Food energy — methods of
  analysis and conversion factors*, 2003).

## #6 — Equivalencia energía/peso: regla de Wishnofsky
- **Aproximación:** 1 kg de grasa corporal ≈ 7700 kcal (~3500 kcal/libra).
- **Caveat:** es una simplificación; el cuerpo se adapta (termogénesis
  adaptativa), así que las estimaciones de ritmo de pérdida son orientativas.
- Wishnofsky M, *Caloric equivalents of gained or lost weight*, Am J Clin Nutr, 1958.

## #7 — Suelos mínimos de calorías (heurística de seguridad)
- **Suelo fisiológico real:** el BMR (no recomendar comer por debajo del gasto
  basal).
- **Suelos absolutos adicionales:** 1500 kcal (hombres) / 1200 kcal (mujeres),
  cifras comúnmente citadas como mínimo para dietas sin supervisión médica.
  No tienen respaldo tan sólido como el resto; se usan solo como red de
  seguridad y deberían revisarse con un profesional en casos reales.

---
_Última verificación: 2026-09-09._

## #8 — Datos de alimentos: Open Food Facts
- **Qué usamos:** info nutricional por 100 g (energía kcal, proteínas, carbos,
  grasas), nombre, marca y código de barras.
- **Endpoints:** producto por código
  `https://world.openfoodfacts.org/api/v2/product/{barcode}.json`; búsqueda de
  texto vía Search-a-licious `https://search.openfoodfacts.org/search` (solo
  devuelve códigos), hidratada con `.../api/v2/search?code=...`.
- **Naturaleza del dato:** base **colaborativa** bajo Open Database License
  (ODbL). NO es una autoridad sanitaria: puede haber errores u omisiones. Por
  eso KCN permite crear y editar alimentos propios y prioriza el código de
  barras (más fiable) frente a la búsqueda por texto.
- **Buenas prácticas:** User-Agent identificativo (requisito de OFF).
- **Fuente:** https://world.openfoodfacts.org ·
  docs https://openfoodfacts.github.io/openfoodfacts-server/api/

  ## #9 — IMC (Índice de Masa Corporal) y clasificación: OMS
- **Fórmula:** IMC = peso(kg) / altura(m)².
- **Categorías (OMS):** <18.5 bajo peso · 18.5–24.9 normopeso · 25–29.9
  sobrepeso · ≥30 obesidad.
- **Caveat importante:** el IMC no distingue músculo de grasa; en personas muy
  musculadas (deportistas) sobreestima el exceso de grasa. Por eso KCN prioriza
  el % de grasa corporal cuando el usuario lo aporta con su báscula.
- **Fuente:** OMS — https://www.who.int/health-topics/obesity

## #10 — Ingesta adecuada de agua: EFSA
- **Valores (agua total/día):** 2,5 L hombres · 2,0 L mujeres (adultos).
- **Nota:** incluye el agua de los alimentos (~20-30%). Es una referencia; con
  ejercicio intenso o calor hay que beber más para reponer el sudor. El usuario
  puede ajustar su objetivo.
- **Fuente:** EFSA (2010), Scientific Opinion on Dietary Reference Values for water.

## #11 — Ciclado de carbohidratos por tipo de día (estrategia)
- **Qué hacemos:** en días de entreno subimos carbohidratos; en descanso los
  bajamos. Proteína (ISSN #3) y grasa (AMDR #4) se mantienen. OPCIONAL y
  desactivado por defecto.
- **Base:** periodización de carbohidratos ("fuel for the work required"),
  práctica habitual en nutrición deportiva.
- **Honestidad:** es una ESTRATEGIA, no una regla exacta. El balance semanal
  depende de tu proporción de días entreno/descanso; con un % moderado y un
  reparto equilibrado apenas altera tu objetivo. Además, registrar el ejercicio
  ya añade margen los días que entrenas.
- **Fuente:** ISSN Nutrient Timing Position Stand (Kerksick et al., 2017),
  J Int Soc Sports Nutr.