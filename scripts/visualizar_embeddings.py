"""Genera docs/visor_embeddings.html: los chunks indexados proyectados a 2D con UMAP.

Lee los vectores directamente de Chroma (colecciones chunks_D y chunks_A), agrega
unas preguntas de prueba como estrellas y los inserta en la plantilla
scripts/plantillas/visor_embeddings.html (Plotly, interactiva).

Uso:
    .venv/bin/python scripts/visualizar_embeddings.py
"""

import json
import sys
from pathlib import Path

import chromadb
import numpy as np
import umap

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.embeddings import embeddear_queries  # noqa: E402

PREGUNTAS = [
    "How did Darius's Q cooldown change in patch 26.21?",
    "What changes did Locke's Q - Ritual Nails receive in patch 26.22?",
    "Why did Riot nerf Thresh in 26.22?",
]


def main() -> None:
    cliente = chromadb.PersistentClient(path=str(RAIZ / "data" / "index" / "chroma"))
    puntos, vectores = [], []
    for coleccion in ("chunks_D", "chunks_A"):
        r = cliente.get_collection(coleccion).get(include=["embeddings", "metadatas", "documents"])
        for i, e, m, d in zip(r["ids"], r["embeddings"], r["metadatas"], r["documents"]):
            vectores.append(e)
            puntos.append({"id": i, "col": coleccion[-1], "patch": m["patch"],
                           "section": m.get("section", ""), "kind": m["kind"],
                           "entity": m.get("entity", ""), "text": d[:420]})
    for q, e in zip(PREGUNTAS, embeddear_queries(PREGUNTAS)):
        vectores.append(e)
        puntos.append({"id": "QUERY", "col": "Q", "patch": "", "section": "", "kind": "query",
                       "entity": "", "text": q})

    xy = umap.UMAP(n_neighbors=15, min_dist=0.1, metric="cosine", random_state=42).fit_transform(
        np.array(vectores))
    for p, (x, y) in zip(puntos, xy):
        p["x"], p["y"] = round(float(x), 3), round(float(y), 3)

    datos = json.dumps(puntos, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    plantilla = (RAIZ / "scripts" / "plantillas" / "visor_embeddings.html").read_text()
    salida = RAIZ / "docs" / "visor_embeddings.html"
    salida.write_text(plantilla.replace("__DATOS__", datos))
    print(f"{len(puntos)} puntos -> {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
