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
# Las armas de Aphelios llevan encabezado propio, pero son parte del campeón.
ARMAS_APHELIOS = {"Calibrum", "Severum", "Gravitum", "Infernum", "Crescendum"}

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
        if RE_HABILIDAD.match(t) or t == "Base Stats" or (
            t in ARMAS_APHELIOS and estado["entity"] == "Aphelios"
        ):
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


# Longitud máxima del tramo de PDF del que se recuperan cambios (caracteres).
# Los casos reales miden menos de 100; un tramo de miles es un límite mal detectado.
MAX_TRAMO = 600


def normalizar_comillas(t: str) -> str:
    return t.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"}))


def patron_cita(cita: str) -> re.Pattern:
    """Regex que encuentra una cita en el texto del PDF a pesar de los saltos de línea."""
    palabras = normalizar_comillas(cita).strip('" ').split()[:8]
    return re.compile(r"\s+".join(map(re.escape, palabras)))


def recuperar_cambios(bloques: list[dict], ruta_pdf: Path) -> list[dict]:
    """Recupera cambios que Docling no entregó, usando la capa de texto del PDF.

    Docling a veces omite la única línea de cambios de un campeón (Draven en 26.19,
    Darius en 26.21): la entidad queda solo con la cita del diseñador. Para cada
    campeón con cita pero sin ningún "⇒", se busca en el texto del PDF el tramo entre
    el final de su cita y el inicio de la cita de la siguiente entidad, y se toman de
    ahí los cambios. Los bloques recuperados se marcan con "recuperado": "pdf-texto".
    """
    import pypdfium2

    pdf = pypdfium2.PdfDocument(ruta_pdf)
    texto = normalizar_comillas(
        "\n".join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf)))
    ).replace("\r\n", "\n")

    # Entidades en orden, con su cita (primer bloque citado) y sus bloques.
    clave = lambda b: (b["section"], b["group"], b["entity"])
    entidades: dict[tuple, list[dict]] = {}
    for b in bloques:
        if b["entity"]:
            entidades.setdefault(clave(b), []).append(b)
    con_cita = [(k, next(b for b in bs if es_cita(b["text"]))["text"])
                for k, bs in entidades.items() if any(es_cita(b["text"]) for b in bs)]

    nuevos: dict[tuple, list[dict]] = {}
    for i, (k, cita) in enumerate(con_cita):
        # Solo campeones sin ningún cambio. Las entidades narrativas ("Council Vote",
        # "Art"...) también tienen cita y no tienen "⇒", pero ahí no falta nada.
        if k[2] not in CAMPEONES or any("⇒" in b["text"] for b in entidades[k]):
            continue
        m = patron_cita(cita).search(texto)
        if not m:
            continue
        inicio = texto.find('"', m.end())  # cierre de la cita
        fin = len(texto)
        if i + 1 < len(con_cita):
            m2 = patron_cita(con_cita[i + 1][1]).search(texto, inicio)
            if m2:
                fin = texto.rfind('"', inicio, m2.start())
        tramo = texto[inicio + 1 : fin]
        siguiente = con_cita[i + 1][0][2] if i + 1 < len(con_cita) else None
        if siguiente and siguiente in tramo:
            tramo = tramo[: tramo.rfind(siguiente)]
        # Un tramo largo indica que no se encontró bien el límite: mejor no recuperar.
        if len(tramo) > MAX_TRAMO:
            continue

        sub, lineas = None, []
        for linea in (l.strip() for l in tramo.split("\n")):
            if not linea:
                continue
            if RE_HABILIDAD.match(linea) or linea == "Base Stats":
                sub = linea
            elif re.match(r"^[A-Z][^:⇒]{0,60}:", linea) or not lineas:
                lineas.append([sub, linea])
            else:
                lineas[-1][1] += " " + linea
        base = entidades[k][0]
        nuevos[k] = [
            {**{c: base[c] for c in ("patch", "section", "group", "entity")},
             "sub": s, "text": limpiar(t), "recuperado": "pdf-texto"}
            for s, t in lineas if "⇒" in t
        ]

    salida = []
    for i, b in enumerate(bloques):
        salida.append(b)
        k = clave(b)
        ultimo = i + 1 == len(bloques) or clave(bloques[i + 1]) != k
        if b["entity"] and ultimo and nuevos.get(k):
            salida.extend(nuevos.pop(k))
    return salida


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
        bloques = recuperar_cambios(bloques, RAIZ / "data" / "raw" / f"{nombre}.pdf")
        recuperados = [b for b in bloques if b.get("recuperado")]
        (DESTINO / f"{nombre}.json").write_text(json.dumps(bloques, ensure_ascii=False, indent=1))
        (DESTINO / f"{nombre}.md").write_text(a_markdown(bloques, parche))
        entidades = {(b["section"], b["entity"]) for b in bloques if b["entity"]}
        print(f"{parche}: {len(bloques)} bloques, {len(entidades)} entidades, "
              f"{len(recuperados)} cambios recuperados del texto del PDF")
        for b in recuperados:
            print(f"    + {b['entity']} · {b['sub']} · {b['text']}")


if __name__ == "__main__":
    main()
