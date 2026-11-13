"""Evaluación de la generación con RAGAS (juez: Claude Sonnet 5.5) y de las trampas.

Lee eval/resultados/generacion.json (lo produce scripts/generar.py).

Métricas RAGAS, sobre las 10 preguntas normales (D-42):
  faithfulness        ¿todo lo que afirma la respuesta está en los chunks recuperados?
  answer_relevancy    ¿la respuesta contesta la pregunta?
  context_precision   ¿los chunks relevantes salieron arriba en el ranking? (contra la respuesta ideal)
  context_recall      ¿los chunks recuperados contienen todo lo de la respuesta ideal?
  answer_correctness  ¿la respuesta coincide con la respuesta ideal?

Trampas (q11, q12): tasa de rechazo correcto, detectada por la frase fija del prompt.
También se revisan rechazos indebidos en las preguntas normales.

Salida: eval/resultados/ragas.json

Uso:
    .venv/bin/python scripts/evaluar_generacion.py
"""

import asyncio
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from ragas.metrics.collections import (  # noqa: E402
    AnswerCorrectness, AnswerRelevancy, ContextPrecisionWithReference, ContextRecall, Faithfulness)

from src.juez import MODELO_JUEZ, EmbeddingsQwen, JuezClaude  # noqa: E402

PRECIO_JUEZ = {"entrada": 2.00e-6, "salida": 10.00e-6}  # Sonnet 5.5, USD por token
CONCURRENCIA = 3


async def evaluar_pregunta(x, metricas, sem) -> dict:
    ctx = [c["text"] for c in x["contexts"]]
    q, resp, ref = x["query"], x["texto_sin_citas"], x["ideal_answer"]
    llamadas = {
        "faithfulness": lambda: metricas["faithfulness"].ascore(user_input=q, response=resp, retrieved_contexts=ctx),
        "answer_relevancy": lambda: metricas["answer_relevancy"].ascore(user_input=q, response=resp),
        "context_precision": lambda: metricas["context_precision"].ascore(user_input=q, reference=ref, retrieved_contexts=ctx),
        "context_recall": lambda: metricas["context_recall"].ascore(user_input=q, retrieved_contexts=ctx, reference=ref),
        "answer_correctness": lambda: metricas["answer_correctness"].ascore(user_input=q, response=resp, reference=ref),
    }
    resultado = {}
    async with sem:
        for nombre, llamar in llamadas.items():
            try:
                resultado[nombre] = round(float((await llamar()).value), 4)
            except Exception as e:  # una métrica fallida no tumba la corrida
                resultado[nombre] = None
                resultado.setdefault("errores", {})[nombre] = f"{type(e).__name__}: {str(e)[:200]}"
    print(f"{x['id']} " + "  ".join(f"{k}={v}" for k, v in resultado.items() if k != "errores"))
    return {"id": x["id"], "query": q, **resultado}


async def main() -> None:
    datos = json.loads((RAIZ / "eval" / "resultados" / "generacion.json").read_text())["resultados"]
    normales = [x for x in datos if not x["trap"]]
    trampas = [x for x in datos if x["trap"]]

    juez, emb = JuezClaude(), EmbeddingsQwen()
    metricas = {
        "faithfulness": Faithfulness(llm=juez),
        "answer_relevancy": AnswerRelevancy(llm=juez, embeddings=emb),
        "context_precision": ContextPrecisionWithReference(llm=juez),
        "context_recall": ContextRecall(llm=juez),
        "answer_correctness": AnswerCorrectness(llm=juez, embeddings=emb),
    }
    sem = asyncio.Semaphore(CONCURRENCIA)
    por_pregunta = await asyncio.gather(*(evaluar_pregunta(x, metricas, sem) for x in normales))

    nombres = list(metricas)
    promedio = {}
    for m in nombres:
        valores = [p[m] for p in por_pregunta if p.get(m) is not None]
        promedio[m] = round(sum(valores) / len(valores), 3) if valores else None

    rechazo = {
        "trampas_rechazadas": sum(x["es_negativa"] for x in trampas),
        "trampas_total": len(trampas),
        "rechazos_indebidos": [x["id"] for x in normales if x["es_negativa"]],
    }
    costo = juez.uso["entrada"] * PRECIO_JUEZ["entrada"] + juez.uso["salida"] * PRECIO_JUEZ["salida"]
    salida = {"juez": MODELO_JUEZ, "n_preguntas": len(normales), "promedio": promedio,
              "rechazo": rechazo, "uso_juez": {**juez.uso, "costo_usd": round(costo, 3)},
              "por_pregunta": por_pregunta}
    (RAIZ / "eval" / "resultados" / "ragas.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1))

    print("\nPromedios:", promedio)
    print("Trampas rechazadas:", f"{rechazo['trampas_rechazadas']}/{rechazo['trampas_total']}",
          "| rechazos indebidos:", rechazo["rechazos_indebidos"] or "ninguno")
    print(f"Juez: {juez.uso['llamadas']} llamadas, costo ≈ USD {costo:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
