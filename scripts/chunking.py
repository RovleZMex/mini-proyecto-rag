"""Paso 3: chunking del corpus procesado.

Genera dos conjuntos de chunks en data/chunks/:

  chunks_D.jsonl  Estrategia principal (D-12): un chunk por habilidad o bloque de stats.
                  - La cita del diseñador de cada entidad es un chunk propio, "Developer note" (D-15).
                  - El contenido que no pertenece a ninguna habilidad (items, augments,
                    descripciones) forma un chunk a nivel de entidad (D-16).
                  - Las unidades de más de MAX_TOKENS se parten entre líneas (D-17).
                  - Cada chunk lleva antepuesto su encabezado de contexto (D-14):
                    "Patch 26.21 › CHAMPIONS › Darius › Q - Decimate".

  chunks_A.jsonl  Línea base (D-13): ventanas fijas de 512 tokens con overlap de 50
                  sobre el Markdown de cada parche, sin encabezado de contexto.

Cada chunk guarda `unit_ids`: las unidades de contenido que contiene. Una unidad es la
combinación parche/sección/grupo/entidad/subsección, y es independiente del chunking.
El ground truth se anota con unit_ids, así sirve para comparar A contra D.

Uso:
    .venv/bin/python scripts/chunking.py
"""

import json
import re
import statistics
from pathlib import Path

import tiktoken

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "data" / "processed"
DESTINO = RAIZ / "data" / "chunks"

MAX_TOKENS = 250  # D-17: tamaño máximo de un chunk de D
FIJO_TOKENS, FIJO_OVERLAP = 512, 50  # D-13: línea base
NOTA_DEV = "Developer note"
NIVELES = ("section", "group", "entity", "sub")

enc = tiktoken.get_encoding("cl100k_base")


def n_tokens(texto: str) -> int:
    return len(enc.encode(texto))


def es_cita(texto: str) -> bool:
    return texto[:1] in {'"', "“"}


def unidad(bloque: dict) -> tuple:
    """Unidad de contenido a la que pertenece un bloque (D-15: la cita va aparte)."""
    sub = bloque["sub"]
    if es_cita(bloque["text"]) and sub is None:
        sub = NOTA_DEV
    return (bloque["patch"], bloque["section"], bloque["group"], bloque["entity"], sub)


def unit_id(u: tuple) -> str:
    return "/".join(p for p in u if p)


def encabezado(u: tuple) -> str:
    return " › ".join([f"Patch {u[0]}", *[p for p in u[1:] if p]])


def tipo(u: tuple) -> str:
    if u[4] == NOTA_DEV:
        return "developer_note"
    if u[4]:
        return "ability_or_stats"
    return "entity" if u[3] else "section"


def oraciones(linea: str) -> list[str]:
    """Parte una línea demasiado larga por oraciones.

    En algunas secciones de modos de juego, Docling unió varios elementos de una
    lista en un solo párrafo (p. ej. todos los bugfixes de Classic en 26.17).
    """
    if n_tokens(linea) <= MAX_TOKENS:
        return [linea]
    return [o for o in re.split(r'(?<=[.!?"])\s+(?=[A-Z"])', linea) if o]


def partir(lineas: list[str], cabecera: str) -> list[list[str]]:
    """D-17: agrupa líneas en trozos de máximo MAX_TOKENS, cortando entre líneas.

    Solo si una línea sola excede el máximo se corta dentro de ella, entre oraciones.
    """
    lineas = [o for linea in lineas for o in oraciones(linea)]
    base = n_tokens(cabecera) + 1
    trozos, actual, tam = [], [], base
    for linea in lineas:
        t = n_tokens(linea) + 1
        if actual and tam + t > MAX_TOKENS:
            trozos.append(actual)
            actual, tam = [], base
        actual.append(linea)
        tam += t
    if actual:
        trozos.append(actual)
    return trozos


def chunks_estructurales(bloques: list[dict]) -> list[dict]:
    unidades: dict[tuple, list[str]] = {}
    for b in bloques:
        unidades.setdefault(unidad(b), []).append(b["text"])

    chunks = []
    for u, lineas in unidades.items():
        cabecera = encabezado(u)
        trozos = partir(lineas, cabecera)
        for i, trozo in enumerate(trozos, start=1):
            texto = cabecera + "\n" + "\n".join(trozo)
            sufijo = f"#{i}" if len(trozos) > 1 else ""
            chunks.append({
                "id": unit_id(u) + sufijo,
                "unit_ids": [unit_id(u)],
                "patch": u[0],
                **{k: v for k, v in zip(NIVELES, u[1:])},
                "kind": tipo(u),
                "n_tokens": n_tokens(texto),
                "text": texto,
            })
    return chunks


def chunks_fijos(markdown: str, parche: str, bloques: list[dict]) -> list[dict]:
    ids = enc.encode(markdown)
    # Para mapear el ground truth: qué unidades contiene cada ventana.
    # Una unidad está en el chunk si el inicio o el final de alguna de sus líneas
    # aparece en él (una línea larga puede quedar partida entre dos ventanas).
    lineas_por_unidad: dict[str, list[str]] = {}
    for b in bloques:
        lineas_por_unidad.setdefault(unit_id(unidad(b)), []).append(b["text"])

    chunks, inicio, n = [], 0, 0
    while inicio < len(ids):
        texto = enc.decode(ids[inicio : inicio + FIJO_TOKENS])
        n += 1
        contenidas = [uid for uid, ls in lineas_por_unidad.items()
                      if any(l[:60] in texto or l[-60:] in texto for l in ls)]
        chunks.append({
            "id": f"{parche}/fixed-{n:03d}",
            "unit_ids": contenidas,
            "patch": parche,
            "kind": "fixed",
            "n_tokens": n_tokens(texto),
            "text": texto,
        })
        if inicio + FIJO_TOKENS >= len(ids):
            break
        inicio += FIJO_TOKENS - FIJO_OVERLAP
    return chunks


def resumen(nombre: str, chunks: list[dict]) -> None:
    tam = sorted(c["n_tokens"] for c in chunks)
    tipos: dict[str, int] = {}
    for c in chunks:
        tipos[c["kind"]] = tipos.get(c["kind"], 0) + 1
    print(f"{nombre}: {len(chunks)} chunks · tokens mediana {statistics.median(tam):.0f}, "
          f"mín {tam[0]}, máx {tam[-1]} · {tipos}")


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    todos_d, todos_a = [], []
    for ruta in sorted(ORIGEN.glob("patch-26-*.json")):
        bloques = json.loads(ruta.read_text())
        parche = bloques[0]["patch"]
        todos_d += chunks_estructurales(bloques)
        todos_a += chunks_fijos(ruta.with_suffix(".md").read_text(), parche, bloques)

    ids = [c["id"] for c in todos_d]
    assert len(ids) == len(set(ids)), "IDs de chunk repetidos en D"

    for nombre, chunks in (("chunks_D.jsonl", todos_d), ("chunks_A.jsonl", todos_a)):
        with open(DESTINO / nombre, "w") as f:
            for c in chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    resumen("D (habilidad + encabezado)", todos_d)
    resumen("A (fijo 512/50)", todos_a)


if __name__ == "__main__":
    main()
