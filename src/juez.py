"""Adaptadores para que RAGAS use Claude Sonnet 5.5 como juez y Qwen3 como embeddings.

Por qué existen (docs/bitacora.md, P-17):
  RAGAS 0.4 se conecta a Anthropic a través de la librería `instructor`, que
  (1) envía `temperature`, un parámetro que el SDK actual de Anthropic ya no acepta, y
  (2) obtiene salidas estructuradas forzando una herramienta (`tool_choice`), lo cual
      Sonnet 5.5 rechaza.
  Este adaptador usa en cambio las salidas estructuradas nativas de la API
  (`messages.parse` con un modelo Pydantic), que es la forma recomendada.

Los embeddings reusan el mismo Qwen3-Embedding-0.6B local del retriever (D-20),
así RAGAS no necesita otra API.
"""

import asyncio
import typing as t

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel
from ragas.embeddings import BaseRagasEmbedding
from ragas.llms.base import InstructorBaseRagasLLM

from src.embeddings import embeddear_documentos
from src.generacion import RAIZ

load_dotenv(RAIZ / ".env")

MODELO_JUEZ = "claude-sonnet-5-5"
M = t.TypeVar("M", bound=BaseModel)


class JuezClaude(InstructorBaseRagasLLM):
    """LLM juez para las métricas de RAGAS."""

    def __init__(self, modelo: str = MODELO_JUEZ):
        self.modelo = modelo
        self.cliente = anthropic.AsyncAnthropic()
        self.uso = {"llamadas": 0, "entrada": 0, "salida": 0}

    async def agenerate(self, prompt: str, response_model: type[M]) -> M:
        r = await self.cliente.messages.parse(
            model=self.modelo,
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}],
            output_format=response_model,
        )
        self.uso["llamadas"] += 1
        self.uso["entrada"] += r.usage.input_tokens
        self.uso["salida"] += r.usage.output_tokens
        if r.stop_reason == "refusal" or r.parsed_output is None:
            raise RuntimeError(f"El juez no devolvió una salida válida (stop_reason={r.stop_reason})")
        return r.parsed_output

    def generate(self, prompt: str, response_model: type[M]) -> M:
        return asyncio.run(self.agenerate(prompt, response_model))


class EmbeddingsQwen(BaseRagasEmbedding):
    """Qwen3-Embedding-0.6B local. Se usa sin instrucción de query: RAGAS compara
    textos del mismo tipo entre sí (pregunta contra preguntas, respuesta contra respuesta)."""

    def embed_text(self, text: str, **kwargs) -> list[float]:
        return embeddear_documentos([text])[0].tolist()

    def embed_texts(self, texts: list[str], **kwargs) -> list[list[float]]:
        return embeddear_documentos(texts).tolist()

    async def aembed_text(self, text: str, **kwargs) -> list[float]:
        return self.embed_text(text)

    async def aembed_texts(self, texts: list[str], **kwargs) -> list[list[float]]:
        return self.embed_texts(texts)
