# Mini-Proyecto RAG (Retrieval-Augmented Generation)

## Objetivo
Diseñar, implementar y evaluar un sistema RAG (Retrieval-Augmented Generation) para responder consultas a partir de un corpus  específico. El objetivo principal es que tomes decisiones de arquitectura justificadas, comparando al menos dos estrategias de recuperación para demostrar empíricamente cuál funciona mejor para tu caso de uso.

## Instrucciones y Lineamientos Base

Tendrás libertad para elegir la temática, los modelos y las herramientas, sujetándote a los siguientes puntos base obligatorios:

### 1. El Corpus
* Escoger entre 5 y 10 archivos PDF/md/etc sobre una misma temática.
* Debes justificar brevemente por qué elegiste esos documentos y los retos específicos de parsing que presentan (ej. tablas, ecuaciones, formato a dos columnas).

### 2. El Dataset de Evaluación (Ground Truth)
* Definir manualmente un set de 10 queries.
* Para cada query, debes anotar el Ground Truth de los documentos/chunks correctos que deberían ser recuperados, así como la respuesta ideal generada.
* Incluir al menos 2 queries "trampa" (información no presente en los PDFs) para evaluar la capacidad del sistema de rechazar la respuesta y evitar alucinaciones.

### 3. Evaluación y Comparación
* Debes implementar y comparar al menos 2 estrategias de Retrieval distintas (ej. Naive Dense Retrieval vs. Hybrid Search con BM25, o Retrieval estándar vs. Retrieval + Reranking).
* Métricas obligatorias para el Retrieval: Debes calcular y reportar Precision@k y Recall@k.
* Métricas para la Generación: Evaluar la calidad de la respuesta final usando RAGAS.

## Entregables y Presentación

La presentación deberá cubrir los 4 aspectos:

1. Arquitectura RAG: Diagrama claro del pipeline. Justificación técnica de las herramientas elegidas (Chunking, Embeddings, Vector DB, LLM). Mostrar en código las líneas clave donde se orquesta el pipeline.
2. Documentos y Procesamiento: Explicación del parsing de los PDFs y la estrategia de chunking (tamaño, overlap, chunking semántico, etc.).
3. Evaluación y Resultados:
   * Tabla comparativa de las 2 estrategias de Retriever (Precision@k y Recall@k).
   * Análisis de errores: ¿En qué queries falló el sistema y por qué?
4. Visión de Producción (Proof of Concept):
   * ¿Cómo harías el deployment de esta solución?
   * ¿Qué servicio/API usarías para el LLM y por qué (costo vs. latencia vs. privacidad)?
   * ¿Cuál es el principal cuello de botella al escalar este sistema a 500 documentos?
