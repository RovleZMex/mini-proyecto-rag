"""Corre el RAG completo sobre las 12 preguntas del ground truth.

Retriever: por habilidad · Hybrid sin cifras (D-36), top-10.
Generador: Claude Haiku 5.5 (src/generacion.py).

Salida: eval/resultados/generacion.json, con los chunks que recibió el modelo,
la respuesta con y sin citas, si fue negativa, los tokens y el tiempo de cada pregunta.

Uso:
    .venv/bin/python scripts/generar.py
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.generacion import EFFORT, MODELO, responder  # noqa: E402
from src.retrievers import HybridRetriever  # noqa: E402


def main() -> None:
    gt = json.loads((RAIZ / "eval" / "ground_truth.json").read_text())["queries"]
    retriever = HybridRetriever("D", quitar_cifras=True)
    salida = []
    for q in gt:
        chunks = retriever.buscar(q["query"], k=10)
        r = responder(q["query"], chunks)
        relevantes = set(q["relevant_units"])
        salida.append({
            "id": q["id"], "trap": q["trap"], "query": q["query"],
            "ideal_answer": q["ideal_answer"],
            "contexts": [{"n": i, "id": c.id, "text": c.text,
                          "relevant": bool(relevantes & set(c.unit_ids))}
                         for i, c in enumerate(chunks, start=1)],
            **asdict(r),
        })
        marca = "NEGATIVA" if r.es_negativa else r.stop_reason
        print(f"{q['id']} {'T' if q['trap'] else ' '} {marca:9} {r.segundos:5.1f}s "
              f"in={r.tokens_entrada} out={r.tokens_salida} citas={r.citas}")

    destino = RAIZ / "eval" / "resultados" / "generacion.json"
    destino.write_text(json.dumps({"modelo": MODELO, "effort": EFFORT,
                                   "retriever": "Por habilidad · Hybrid sin cifras",
                                   "resultados": salida}, ensure_ascii=False, indent=1))
    tin = sum(x["tokens_entrada"] for x in salida); tout = sum(x["tokens_salida"] for x in salida)
    print(f"\nTokens: {tin} entrada, {tout} salida · costo ≈ USD {tin * 0.10e-6 + tout * 0.50e-6:.4f}")


if __name__ == "__main__":
    main()
