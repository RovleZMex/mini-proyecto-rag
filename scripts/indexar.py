"""Paso 4: indexado de los chunks en Chroma con Qwen3-Embedding-0.6B.

Crea dos colecciones en data/index/chroma/ (se regeneran desde cero en cada corrida):
  chunks_D  estrategia principal (habilidad + encabezado de contexto)
  chunks_A  línea base (tamaño fijo 512/50)

Decisiones (ver docs/bitacora.md, D-20 a D-22):
  - Modelo: Qwen/Qwen3-Embedding-0.6B, local en MPS. Los documentos se embeddean
    sin instrucción; las queries usan el prompt "query" del modelo (src/embeddings.py).
  - Vectores normalizados y distancia coseno en Chroma.
  - Chroma no acepta None ni listas como metadatos: None se guarda como "" y
    unit_ids como texto JSON.

Uso:
    .venv/bin/python scripts/indexar.py
"""

import json
import sys
import time
from pathlib import Path

import chromadb

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.embeddings import MODELO, embeddear_documentos  # noqa: E402

CHUNKS = RAIZ / "data" / "chunks"
INDICE = RAIZ / "data" / "index" / "chroma"
METADATOS = ("patch", "section", "group", "entity", "sub", "kind", "n_tokens")


def cargar(nombre: str) -> list[dict]:
    with open(CHUNKS / f"chunks_{nombre}.jsonl") as f:
        return [json.loads(linea) for linea in f]


def metadatos(chunk: dict) -> dict:
    meta = {k: ("" if chunk.get(k) is None else chunk[k]) for k in METADATOS}
    meta["unit_ids"] = json.dumps(chunk["unit_ids"], ensure_ascii=False)
    return meta


def main() -> None:
    cliente = chromadb.PersistentClient(path=str(INDICE))
    for nombre in ("D", "A"):
        chunks = cargar(nombre)
        inicio = time.time()
        vectores = embeddear_documentos([c["text"] for c in chunks])
        segundos = time.time() - inicio

        coleccion = f"chunks_{nombre}"
        if coleccion in [c.name for c in cliente.list_collections()]:
            cliente.delete_collection(coleccion)
        col = cliente.create_collection(
            coleccion,
            metadata={"hnsw:space": "cosine", "modelo": MODELO},
        )
        for i in range(0, len(chunks), 500):  # Chroma limita el tamaño de cada lote
            lote = chunks[i : i + 500]
            col.add(
                ids=[c["id"] for c in lote],
                documents=[c["text"] for c in lote],
                embeddings=vectores[i : i + 500].tolist(),
                metadatas=[metadatos(c) for c in lote],
            )
        print(f"{coleccion}: {col.count()} chunks indexados · embeddings en {segundos:.0f} s")


if __name__ == "__main__":
    main()
