"""Generación: Claude Haiku 5.5 responde a partir de los chunks recuperados.

Decisiones (docs/bitacora.md, D-38 y D-41):
  - Modelo claude-haiku-5-5, effort "medium" (su valor por defecto, explícito).
  - Solo puede usar el contexto; nada de lo que sabe del juego.
  - Negativa con una frase fija, para detectar automáticamente si rechazó.
  - Si la información es parcial, responde lo que hay y dice qué falta.
  - Cita los chunks usados con su número, [n]. Las citas se quitan antes de RAGAS.
"""

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

MODELO = "claude-haiku-5-5"
EFFORT = "medium"
NEGATIVA = "The provided patch notes do not contain this information."

SYSTEM = f"""You answer questions about League of Legends patch notes using ONLY the excerpts provided in <context>. Each excerpt starts with its location, e.g. "Patch 26.22 › CHAMPIONS › Locke › Q - Ritual Nails".

Rules:
1. Use only facts stated in the excerpts. Do not use outside knowledge about the game, even if you believe you know the answer.
2. Always state which patch each fact comes from.
3. Report numbers exactly as written, with their before ⇒ after values.
4. If the excerpts do not contain the answer, reply exactly:
   "{NEGATIVA}"
5. If they contain only part of the answer, give that part and say explicitly what is missing.
6. Cite the excerpts you used with their number, like [2]."""

RE_CITA = re.compile(r"\s*\[\d+(?:\s*,\s*\d+)*\]")

_cliente: anthropic.Anthropic | None = None


def cliente() -> anthropic.Anthropic:
    global _cliente
    if _cliente is None:
        _cliente = anthropic.Anthropic()
    return _cliente


def armar_contexto(chunks) -> str:
    partes = [f"[{i}] {c.text}" for i, c in enumerate(chunks, start=1)]
    return "<context>\n" + "\n\n".join(partes) + "\n</context>"


def quitar_citas(texto: str) -> str:
    return RE_CITA.sub("", texto).strip()


@dataclass
class Respuesta:
    texto: str
    texto_sin_citas: str
    es_negativa: bool
    stop_reason: str
    tokens_entrada: int
    tokens_salida: int
    segundos: float
    citas: list[int] = field(default_factory=list)


def responder(pregunta: str, chunks) -> Respuesta:
    inicio = time.time()
    r = cliente().messages.create(
        model=MODELO,
        max_tokens=16000,
        output_config={"effort": EFFORT},
        system=SYSTEM,
        messages=[{"role": "user", "content": f"{armar_contexto(chunks)}\n\nQuestion: {pregunta}"}],
    )
    segundos = time.time() - inicio
    if r.stop_reason == "refusal":
        texto = ""
    else:
        texto = "".join(b.text for b in r.content if b.type == "text").strip()
    citas = sorted({int(n) for grupo in re.findall(r"\[([\d,\s]+)\]", texto)
                    for n in grupo.split(",") if n.strip()})
    return Respuesta(
        texto=texto,
        texto_sin_citas=quitar_citas(texto),
        es_negativa=NEGATIVA.rstrip(".").lower() in texto.lower(),
        stop_reason=r.stop_reason,
        tokens_entrada=r.usage.input_tokens,
        tokens_salida=r.usage.output_tokens,
        segundos=round(segundos, 2),
        citas=citas,
    )
