"""Los dos retrievers que se comparan: Dense e Hybrid (BM25 + Dense con RRF).

Los tres comparten la misma interfaz:

    retriever.buscar(query, k=10) -> list[Resultado]

así la evaluación los trata igual. Cada retriever trabaja sobre un conjunto de
chunks ("D" o "A"), de modo que hay 4 combinaciones para evaluar.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import chromadb
import numpy as np
from rank_bm25 import BM25Okapi

from src.embeddings import embeddear_queries
from src.tokenizador import tokenizar

RAIZ = Path(__file__).resolve().parent.parent
TOP_K = 10      # D-25
RRF_K = 60      # D-24


@dataclass
class Resultado:
    id: str
    score: float
    unit_ids: list[str]
    text: str


@lru_cache(maxsize=2)
def cargar_chunks(conjunto: str) -> list[dict]:
    with open(RAIZ / "data" / "chunks" / f"chunks_{conjunto}.jsonl") as f:
        return [json.loads(linea) for linea in f]


class DenseRetriever:
    """Similitud coseno entre el embedding de la query y los de los chunks.

    Los vectores, textos y metadatos se leen de Chroma, pero la búsqueda es
    EXACTA (producto punto contra todos los vectores, ya normalizados) y no la
    aproximada de Chroma (HNSW). Con la configuración de Chroma, HNSW omitía
    en algunas preguntas un chunk que la búsqueda exacta sí encuentra, aun
    con ef_search = 200 (P-16). Con ~1,150 vectores, la búsqueda exacta tarda
    menos de un milisegundo.
    """

    nombre = "dense"

    def __init__(self, conjunto: str):
        cliente = chromadb.PersistentClient(path=str(RAIZ / "data" / "index" / "chroma"))
        datos = cliente.get_collection(f"chunks_{conjunto}").get(
            include=["embeddings", "metadatas", "documents"])
        self.ids = datos["ids"]
        self.vectores = np.asarray(datos["embeddings"], dtype=np.float32)
        self.unit_ids = [json.loads(m["unit_ids"]) for m in datos["metadatas"]]
        self.textos = datos["documents"]

    def buscar(self, query: str, k: int = TOP_K) -> list[Resultado]:
        vector = embeddear_queries([query])[0].astype(np.float32)
        similitud = self.vectores @ vector
        orden = np.argsort(-similitud, kind="stable")[:k]
        return [Resultado(self.ids[i], float(similitud[i]), self.unit_ids[i], self.textos[i])
                for i in orden]


class BM25Retriever:
    """BM25 (Okapi) con el tokenizador de dominio (D-26)."""

    nombre = "bm25"

    def __init__(self, conjunto: str, quitar_cifras: bool = False):
        self.chunks = cargar_chunks(conjunto)
        self.quitar_cifras = quitar_cifras
        self.bm25 = BM25Okapi([tokenizar(c["text"], quitar_cifras) for c in self.chunks])

    def buscar(self, query: str, k: int = TOP_K) -> list[Resultado]:
        scores = self.bm25.get_scores(tokenizar(query, self.quitar_cifras))
        orden = sorted(range(len(self.chunks)), key=lambda i: -scores[i])[:k]
        return [Resultado(self.chunks[i]["id"], float(scores[i]), self.chunks[i]["unit_ids"],
                          self.chunks[i]["text"]) for i in orden]


class HybridRetriever:
    """Fusiona los rankings de BM25 y Dense con Reciprocal Rank Fusion.

        score_RRF(chunk) = Σ_retrievers 1 / (RRF_K + rank_en_ese_retriever)

    RRF solo usa las posiciones, no los puntajes. Por eso no hace falta poner en la
    misma escala el puntaje de BM25 (0-30) y la similitud coseno (0-1).
    Se fusionan los rankings completos de ambos retrievers (D-28).
    """

    nombre = "hybrid"

    def __init__(self, conjunto: str, quitar_cifras: bool = False):
        self.dense = DenseRetriever(conjunto)
        self.bm25 = BM25Retriever(conjunto, quitar_cifras)
        self.total = len(self.bm25.chunks)

    def buscar(self, query: str, k: int = TOP_K) -> list[Resultado]:
        rankings = [self.dense.buscar(query, self.total), self.bm25.buscar(query, self.total)]
        fusion: dict[str, float] = {}
        por_id: dict[str, Resultado] = {}
        for ranking in rankings:
            for rank, r in enumerate(ranking, start=1):
                fusion[r.id] = fusion.get(r.id, 0.0) + 1 / (RRF_K + rank)
                por_id[r.id] = r
        mejores = sorted(fusion, key=lambda i: -fusion[i])[:k]
        return [Resultado(i, fusion[i], por_id[i].unit_ids, por_id[i].text) for i in mejores]
