# Mini-Proyecto RAG

Sistema RAG (Retrieval-Augmented Generation) para responder consultas sobre un corpus de 5–10 documentos de una misma temática, comparando al menos dos estrategias de recuperación.

Enunciado completo: [docs/enunciado.md](docs/enunciado.md)

## Estructura

```
data/raw/         # documentos originales del corpus (PDF/md)
data/interim/     # salida cruda de Docling (no versionada)
data/processed/   # texto parseado y limpio (JSON + Markdown)
eval/             # ground truth: 10 queries (incluye ≥2 trampa) y resultados
src/              # pipeline: parsing, chunking, embeddings, retrieval, generación
notebooks/        # experimentos y análisis
docs/             # enunciado, bitácora de decisiones, diagramas y presentación
```

## Entregables

1. Arquitectura RAG (diagrama, justificación de herramientas, código clave)
2. Parsing de documentos y estrategia de chunking
3. Evaluación: Precision@k, Recall@k de 2 retrievers + RAGAS para la generación; análisis de errores
4. Visión de producción (deployment, elección de LLM, cuello de botella a 500 documentos)

## Demo local

Una app de Streamlit para hacer preguntas en vivo. Muestra la respuesta de Claude Haiku 5.5 con sus citas y los chunks que recuperan Dense e Hybrid, lado a lado.

```bash
cp .env.example .env              # y escribe tu ANTHROPIC_API_KEY en .env
.venv/bin/streamlit run app.py    # abre http://localhost:8501
```

- **La clave:** `.env` está en `.gitignore`, así que la clave nunca se sube al repositorio.
- **Sin clave:** la app muestra el retrieval, pero no genera la respuesta.
- **Requisitos:** los índices tienen que existir. Si no existen, corre antes `scripts/indexar.py`.
