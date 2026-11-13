"""Evaluación del retrieval: Precision@k, Recall@k y MRR para 6 configuraciones.

Definiciones (docs/bitacora.md, D-32 a D-35):
  - Un chunk es relevante si contiene al menos una unidad relevante de la pregunta.
  - Precision@k = chunks relevantes en los top-k / k
  - Recall@k    = unidades relevantes cubiertas por los top-k / unidades relevantes
  - MRR         = promedio de 1 / posición del primer chunk relevante (0 si no hay en el top-10)
  - Las preguntas trampa (sin unidades relevantes) se excluyen: se evalúan en la generación.
  - k = 1, 3, 5, 10, todos a partir del mismo top-10.

Salida en eval/resultados/:
  retrieval_resumen.json   promedios por configuración
  retrieval_detalle.json   por pregunta y configuración: chunks recuperados y métricas

Uso:
    .venv/bin/python scripts/evaluar_retrieval.py
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.retrievers import BM25Retriever, DenseRetriever, HybridRetriever  # noqa: E402

KS = (1, 3, 5, 10)
SALIDA = RAIZ / "eval" / "resultados"

# Nombre descriptivo -> constructor. "D" = chunking por habilidad, "A" = tamaño fijo.
CONFIGURACIONES = {
    "Por habilidad · Dense": lambda: DenseRetriever("D"),
    "Por habilidad · Hybrid": lambda: HybridRetriever("D"),
    "Tamaño fijo · Dense": lambda: DenseRetriever("A"),
    "Tamaño fijo · Hybrid": lambda: HybridRetriever("A"),
    "Por habilidad · BM25 solo": lambda: BM25Retriever("D"),
    "Por habilidad · Hybrid sin cifras": lambda: HybridRetriever("D", quitar_cifras=True),
}


def metricas(resultados, relevantes: set[str]) -> dict:
    es_rel = [bool(relevantes & set(r.unit_ids)) for r in resultados]
    m = {}
    for k in KS:
        cubiertas = relevantes & {u for r in resultados[:k] for u in r.unit_ids}
        m[f"P@{k}"] = sum(es_rel[:k]) / k
        m[f"R@{k}"] = len(cubiertas) / len(relevantes)
    primera = next((i for i, x in enumerate(es_rel, start=1) if x), None)
    m["MRR"] = 1 / primera if primera else 0.0
    return m


def main() -> None:
    gt = json.loads((RAIZ / "eval" / "ground_truth.json").read_text())["queries"]
    preguntas = [q for q in gt if not q["trap"]]
    SALIDA.mkdir(parents=True, exist_ok=True)

    resumen, detalle = {}, {}
    for nombre, crear in CONFIGURACIONES.items():
        retriever = crear()
        filas = []
        for q in preguntas:
            res = retriever.buscar(q["query"], k=max(KS))
            m = metricas(res, set(q["relevant_units"]))
            filas.append(m)
            detalle.setdefault(q["id"], {"query": q["query"], "relevant_units": q["relevant_units"],
                                         "configs": {}})
            detalle[q["id"]]["configs"][nombre] = {
                "metrics": m,
                "retrieved": [{"id": r.id, "score": round(r.score, 4),
                               "relevant": bool(set(q["relevant_units"]) & set(r.unit_ids))}
                              for r in res],
            }
        resumen[nombre] = {k: round(sum(f[k] for f in filas) / len(filas), 3) for k in filas[0]}
        print(f"{nombre:36} " + "  ".join(f"{k}={v:.2f}" for k, v in resumen[nombre].items()))

    (SALIDA / "retrieval_resumen.json").write_text(json.dumps(
        {"n_preguntas": len(preguntas), "ks": KS, "resumen": resumen}, ensure_ascii=False, indent=1))
    (SALIDA / "retrieval_detalle.json").write_text(json.dumps(detalle, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
