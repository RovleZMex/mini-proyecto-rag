"""Paso 2 del parsing: de JSON de Docling a texto estructurado y limpio.

Docling extrae bien el texto, pero la jerarquía que asigna no es confiable:
  - el mismo tipo de encabezado sale a veces como section_header y a veces como text;
  - algunos encabezados de habilidad quedan "dentro" del ícono (hijos de un picture)
    y export_to_markdown() los omite;
  - todos los encabezados salen al mismo nivel (##).

Por eso aquí se recorre el documento en orden de lectura (incluyendo texto dentro
de imágenes) y se reconstruye la jerarquía con reglas propias del dominio:

  sección   CHAMPIONS, ITEMS, ARAM: MAYHEM, CLASSIC...    (texto en mayúsculas)
  grupo     Champions, Items, Augments, Bugfixes...       (subdivisiones dentro de un modo)
  entidad   Mel, Doran's Bow, Hecarim...                  (enlace a /champions/ o /how-to-play/,
                                                           o línea corta seguida de la cita del diseñador)
  sub       Base Stats, Q - Radiant Volley...             (estadísticas y habilidades)

Salida por parche en data/processed/:
  patch-26-XX.json  lista de bloques {patch, section, group, entity, sub, text}
  patch-26-XX.md    el mismo contenido como Markdown con niveles # a ####

Uso:
    .venv/bin/python scripts/parsear_corpus.py
"""

import html
import json
import re
from pathlib import Path

from docling_core.types.doc import DoclingDocument

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "data" / "interim"
DESTINO = RAIZ / "data" / "processed"

# Secciones que no aportan información al corpus.
SECCIONES_DESCARTADAS = {"TABLE OF CONTENTS", "RELATED ARTICLES"}

# Modos de juego con sus propias subdivisiones.
MODOS = {"CLASSIC", "ARAM: MAYHEM", "ARAM", "ARENA"}

# Subdivisiones que aparecen dentro de los modos de juego (Classic, Arena, Mayhem...).
GRUPOS = {
    "Champions", "Items", "Augments", "Bugfixes", "Systems", "Headliners",
    "New Augments", "Removed Augments", "Runes", "Summoner Spells", "Quests",
    "Bugfixes & QoL Changes",
}

RE_HABILIDAD = re.compile(r"^(Passive|P|Q|W|E|R|R[QWE])\s*[-–]\s*\S")
RE_NUEVO = re.compile(r"^NEW\s*-?\s*")

# Nombres oficiales de campeones (Data Dragon). Sirven para separar líneas que
# Docling unió, como "Q - Decimate Jinx" (habilidad de Darius + siguiente campeón).
CAMPEONES = json.loads((RAIZ / "data" / "campeones.json").read_text())["champions"]
RE_AUTOR = re.compile(r'^[A-Z .\'-]+ "RIOT [A-Z0-9 ]+" [A-Z .\'-]+$')
RE_RUIDO = re.compile(r"^(\+|[A-Z]|曲)$")  # restos de íconos: "Q", "U", "+", etc.


def limpiar(texto: str) -> str:
    texto = html.unescape(texto).replace(" ", " ")
    return re.sub(r"\s+", " ", texto).strip()


def es_seccion(t: str) -> bool:
    letras = [c for c in t if c.isalpha()]
    return len(letras) >= 4 and t.isupper() and not RE_AUTOR.match(t)


def es_cita(t: str) -> bool:
    return t[:1] in {'"', "“"}


def es_entidad_sin_enlace(t: str, etiqueta: str, siguiente: str) -> bool:
    """Nombres de campeón o item que Docling no marcó con enlace."""
    if etiqueta == "section_header":
        return True
    corta = len(t) <= 45 and not any(c in t for c in ":⇒.!?")
    return corta and t[:1].isupper() and es_cita(siguiente)


def elementos(doc: DoclingDocument):
    """Texto en orden de lectura, incluyendo el que Docling dejó dentro de imágenes."""
    for item, _ in doc.iterate_items(with_groups=False, traverse_pictures=True):
        texto = getattr(item, "text", None)
        if not texto:
            continue
        enlace = str(item.hyperlink) if getattr(item, "hyperlink", None) else ""
        yield limpiar(texto), str(item.label), enlace


def separar_lineas_unidas(items: list[tuple]) -> list[tuple]:
    """'Q - Decimate Jinx' seguido de una cita -> 'Q - Decimate' + entidad 'Jinx'."""
    salida = []
    for i, (t, etiqueta, enlace) in enumerate(items):
        siguiente = items[i + 1][0] if i + 1 < len(items) else ""
        if RE_HABILIDAD.match(t) and es_cita(siguiente):
            campeon = next((c for c in CAMPEONES if t.endswith(" " + c)), None)
            if campeon:
                salida.append((t[: -len(campeon)].strip(), etiqueta, ""))
                salida.append((campeon, "section_header", ""))
                continue
        salida.append((t, etiqueta, enlace))
    return salida


def parsear(doc: DoclingDocument, parche: str) -> list[dict]:
    items = [e for e in elementos(doc) if e[0] and not RE_RUIDO.match(e[0])]
    items = separar_lineas_unidas(items)
    vistas: set[str] = set()  # secciones principales ya abiertas
    bloques: list[dict] = []
    estado = {"section": "OVERVIEW", "group": None, "entity": None, "sub": None}

    for i, (t, etiqueta, enlace) in enumerate(items):
        siguiente = items[i + 1][0] if i + 1 < len(items) else ""

        if t.startswith(f"LEAGUE OF LEGENDS PATCH") or RE_AUTOR.match(t):
            continue
        if RE_HABILIDAD.match(t) or t == "Base Stats":
            estado["sub"] = t
            continue
        if es_seccion(t) and t.startswith("GAME UPDATES"):
            break  # a partir de aquí todo es pie de página (artículos relacionados)
        # Dentro de un modo de juego, los encabezados en mayúsculas suelen ser
        # subdivisiones (CHAMPIONS, AUGMENTS, BUGFIXES) o nombres de augments (RISE!).
        # También un encabezado que ya apareció es subdivisión, no sección nueva.
        en_modo = estado["section"] in MODOS
        if es_seccion(t) and (t in vistas or (en_modo and t.title() in GRUPOS)):
            estado.update(group=t.title(), entity=None, sub=None)
            continue
        if es_seccion(t) and en_modo and "!" in t:
            estado.update(entity=t, sub=None)
            continue
        if es_seccion(t):
            vistas.add(t)
            estado.update(section=t, group=None, entity=None, sub=None)
            continue
        if estado["section"] in SECCIONES_DESCARTADAS:
            continue
        if t in GRUPOS:
            estado.update(group=t, entity=None, sub=None)
            continue
        if "/champions/" in enlace or "/how-to-play/" in enlace or (
            estado["section"] != "OVERVIEW" and es_entidad_sin_enlace(t, etiqueta, siguiente)
        ):
            estado.update(entity=RE_NUEVO.sub("", t), sub=None)
            continue

        bloques.append({"patch": parche, **estado, "text": t})
    return bloques


def a_markdown(bloques: list[dict], parche: str) -> str:
    niveles = ("section", "group", "entity", "sub")
    lineas = [f"# Patch {parche}"]
    previo: tuple = (None,) * len(niveles)
    for b in bloques:
        actual = tuple(b[k] for k in niveles)
        # El primer nivel que cambia y todos los de abajo llevan encabezado nuevo.
        cambio = next((i for i in range(len(niveles)) if actual[i] != previo[i]), None)
        if cambio is not None:
            for i in range(cambio, len(niveles)):
                if actual[i]:
                    lineas += ["", f"{'#' * (i + 2)} {actual[i]}"]
        previo = actual
        lineas.append(f"> {b['text']}" if es_cita(b["text"]) else f"- {b['text']}")
    return "\n".join(lineas) + "\n"


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for ruta in sorted(ORIGEN.glob("patch-26-*.docling.json")):
        nombre = ruta.name.removesuffix(".docling.json")
        parche = nombre.removeprefix("patch-").replace("-", ".")
        bloques = parsear(DoclingDocument.load_from_json(ruta), parche)
        (DESTINO / f"{nombre}.json").write_text(json.dumps(bloques, ensure_ascii=False, indent=1))
        (DESTINO / f"{nombre}.md").write_text(a_markdown(bloques, parche))
        entidades = {(b["section"], b["entity"]) for b in bloques if b["entity"]}
        print(f"{parche}: {len(bloques)} bloques, {len(entidades)} entidades")


if __name__ == "__main__":
    main()
