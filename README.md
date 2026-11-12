# Mini-Proyecto RAG

Sistema RAG (Retrieval-Augmented Generation) para responder consultas sobre un corpus de 5–10 documentos de una misma temática, comparando al menos dos estrategias de recuperación.

Enunciado completo: [docs/enunciado.md](docs/enunciado.md)

## Estructura

```
data/raw/         # documentos originales del corpus (PDF/md)
data/processed/   # texto parseado y chunks
eval/             # ground truth: 10 queries (incluye ≥2 trampa) y resultados
src/              # pipeline: parsing, chunking, embeddings, retrieval, generación
notebooks/        # experimentos y análisis
docs/             # enunciado, diagramas y presentación
```

## Entregables

1. Arquitectura RAG (diagrama, justificación de herramientas, código clave)
2. Parsing de documentos y estrategia de chunking
3. Evaluación: Precision@k, Recall@k de 2 retrievers + RAGAS para la generación; análisis de errores
4. Visión de producción (deployment, elección de LLM, cuello de botella a 500 documentos)
