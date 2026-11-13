"""Modelo de embeddings compartido por el indexado y los retrievers.

Qwen3-Embedding es asimétrico: las queries llevan una instrucción antepuesta
(el prompt "query" que trae el modelo) y los documentos no. Si una query se
embeddea sin la instrucción, la calidad baja sin dar ningún error; por eso las
dos funciones viven aquí y nadie llama a model.encode directamente.
"""

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODELO = "Qwen/Qwen3-Embedding-0.6B"


@lru_cache(maxsize=1)
def modelo() -> SentenceTransformer:
    import torch

    dispositivo = "mps" if torch.backends.mps.is_available() else "cpu"
    return SentenceTransformer(MODELO, device=dispositivo)


def embeddear_documentos(textos: list[str], batch_size: int = 16) -> np.ndarray:
    return modelo().encode(
        textos, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True
    )


def embeddear_queries(queries: list[str]) -> np.ndarray:
    return modelo().encode(queries, prompt_name="query", normalize_embeddings=True)
