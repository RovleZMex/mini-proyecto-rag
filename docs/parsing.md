# Preparación del corpus

## Corpus

Notas oficiales de Riot de los parches **26.15 a 26.22** de League of Legends (29 jul – 4 nov 2026), 8 documentos en inglés. Se eligieron porque son posteriores a la fecha de corte de los LLM actuales: si el sistema responde bien, el dato viene del retrieval y no de la memoria del modelo.

## Pipeline

```
leagueoflegends.com ──Playwright──▶ data/raw/*.pdf ──Docling──▶ data/interim/*.docling.json ──reglas──▶ data/processed/*.json / *.md
                     descargar_corpus.py         convertir_docling.py                 parsear_corpus.py
```

| Paso | Script | Salida |
|---|---|---|
| Descarga e impresión a PDF | `scripts/descargar_corpus.py` | `data/raw/patch-26-XX.pdf` (+ `.html` de referencia) |
| Conversión con Docling (sin OCR) | `scripts/convertir_docling.py` | `data/interim/patch-26-XX.docling.json` |
| Limpieza y jerarquía | `scripts/parsear_corpus.py` | `data/processed/patch-26-XX.json` y `.md` |

Cada bloque de `data/processed/*.json` es una línea de contenido con su posición en la jerarquía:

```json
{"patch": "26.22", "section": "CHAMPIONS", "group": null, "entity": "Mel",
 "sub": "Q - Radiant Volley", "text": "Mana Cost: 70 / 75 / 80 / 85 / 90 ⇒ 60 / 65 / 70 / 75 / 80"}
```

## Retos de parsing encontrados

1. **Barra de navegación fija sobre el contenido.** Al imprimir la página, Chromium repetía la barra de Riot encima de cada hoja del PDF y tapaba texto (por ejemplo "R - The Box" de Thresh). Además, las tarjetas de cambios quedaban partidas entre dos páginas y Docling mezclaba el orden de lectura. *Solución:* ocultar los elementos `fixed`/`sticky` y aplicar `break-inside: avoid` a las tarjetas antes de imprimir.
2. **OCR innecesario.** El PDF ya trae capa de texto. Con OCR activado, Docling intentaba leer los íconos de habilidades y metía caracteres basura ("曲"). *Solución:* `do_ocr=False`, que además baja el tiempo de ~150 s a ~10 s por documento.
3. **Encabezados dentro de imágenes.** Docling agrupa a veces el ícono de una habilidad con su título ("E - Singularity") como un solo `picture`, y `export_to_markdown()` omite ese texto. *Solución:* recorrer el documento con `traverse_pictures=True`.
4. **Jerarquía inconsistente.** El mismo tipo de encabezado sale como `section_header` o como `text`, y todos al mismo nivel. *Solución:* reconstruir la jerarquía con reglas del dominio: enlaces a `/champions/` e `/how-to-play/`, el patrón "Q - Nombre", la cita del diseñador que sigue a cada nombre y los encabezados en mayúsculas.
5. **Líneas unidas.** Docling juntó el título de una habilidad con el nombre del siguiente campeón ("Q - Decimate Jinx"). *Solución:* separar usando la lista oficial de campeones de Data Dragon (`data/campeones.json`).
6. **Encabezados repetidos por modo.** "CHAMPIONS", "AUGMENTS" y "BUGFIXES" aparecen también dentro de Classic, ARAM: Mayhem y Arena. *Solución:* dentro de un modo se tratan como subdivisiones, no como secciones nuevas.
7. **Pie de página.** Artículos relacionados y avisos de cookies. *Solución:* cortar en el primer "GAME UPDATES <fecha>".

## Validación

El HTML original sirve como referencia independiente:

| Métrica | Resultado |
|---|---|
| Campeones e items de la Grieta (encabezados `h3` del HTML) detectados como entidad | **140 / 140** |
| Cambios "antes ⇒ después" del PDF conservados en el JSON | **931 / 933** |

Los 2 cambios perdidos (Base Stats de un campeón en 26.19 y un cooldown en 26.21) no aparecen en la salida de Docling. Es una pérdida del propio parser, no de las reglas.

**Errores conocidos que se dejan así:**
- **26.19:** las armas de Aphelios quedan como entidades separadas.
- **26.20:** "Scoreboard Cleanup" queda dentro de ITEMS.
