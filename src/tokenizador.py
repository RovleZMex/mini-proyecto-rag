"""Tokenizador de dominio para BM25 (D-26).

Reglas, en orden:
  1. Minúsculas.
  2. Posesivos fuera: "darius's" -> "darius".
  3. Apóstrofos internos unidos: "vel'koz" -> "velkoz", "kai'sa" -> "kaisa".
  4. Tokens = números con punto ("26.21" queda entero) o secuencias de letras y dígitos.
     Los tokens de una letra se conservan: Q, W, E y R son teclas de habilidad.
  5. Stopwords fuera.
  6. Stemming de Porter, salvo nombres de campeón (Data Dragon): sin esto "Locke"
     se vuelve "lock" y choca con "locked out" / "lock down".
  7. Opcional (quitar_cifras=True): descartar cifras, salvo el número de parche. Las
     cifras alargan el chunk y BM25 lo penaliza por longitud. Es el interruptor de
     D-27, que se decide con el ground truth.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from nltk.stem import PorterStemmer

RAIZ = Path(__file__).resolve().parent.parent

STOPWORDS = frozenset(
    "a an the of in on to for and or is are was were be been did do does how what why "
    "which who with by at from as it its this that these those has have had will would "
    "can could should into than then so".split()
)
RE_POSESIVO = re.compile(r"(\w)'s\b")
RE_APOSTROFO = re.compile(r"(\w)['’](\w)")
RE_TOKEN = re.compile(r"\d+\.\d+|\w+")
RE_PARCHE = re.compile(r"26\.\d{2}")
RE_CIFRA = re.compile(r"\d+(\.\d+)?[a-z]?")  # 75.6, 5s, 300...

_stemmer = PorterStemmer()


@lru_cache(maxsize=1)
def nombres_protegidos() -> frozenset[str]:
    """Nombres de campeón tal como quedan tras las reglas 1-4 ("velkoz", "jarvan", "iv"...)."""
    campeones = json.loads((RAIZ / "data" / "campeones.json").read_text())["champions"]
    nombres = set()
    for c in campeones:
        nombres.update(RE_TOKEN.findall(RE_APOSTROFO.sub(r"\1\2", c.lower())))
    return frozenset(n for n in nombres if len(n) > 2)


def tokenizar(texto: str, quitar_cifras: bool = False) -> list[str]:
    texto = RE_APOSTROFO.sub(r"\1\2", RE_POSESIVO.sub(r"\1", texto.lower()))
    protegidos = nombres_protegidos()
    tokens = []
    for t in RE_TOKEN.findall(texto):
        if t in STOPWORDS:
            continue
        if RE_PARCHE.fullmatch(t):
            tokens.append(t)
        elif RE_CIFRA.fullmatch(t):
            if not quitar_cifras:
                tokens.append(t)
        else:
            tokens.append(t if t in protegidos else _stemmer.stem(t))
    return tokens
