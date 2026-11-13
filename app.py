"""Demo local del RAG sobre notas de parche de League of Legends.

Uso:
    1. Copiar .env.example a .env y poner la API key de Anthropic (nunca se sube al repo).
    2. .venv/bin/streamlit run app.py

Muestra, para una pregunta: los chunks que recupera cada retriever (Dense y Hybrid,
lado a lado) y la respuesta de Claude Haiku 5.5 con el retriever elegido.
"""

import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
load_dotenv(RAIZ / ".env")

st.set_page_config(page_title="RAG · Notas de parche de LoL", layout="wide")


@st.cache_resource(show_spinner="Cargando el modelo de embeddings y los índices…")
def cargar_retrievers():
    from src.retrievers import DenseRetriever, HybridRetriever
    return {
        "Hybrid sin cifras (el del sistema)": HybridRetriever("D", quitar_cifras=True),
        "Dense": DenseRetriever("D"),
    }


@st.cache_data
def preguntas_ground_truth() -> list[str]:
    gt = json.loads((RAIZ / "eval" / "ground_truth.json").read_text())["queries"]
    return [q["query"] for q in gt]


def mostrar_chunks(resultados):
    for i, r in enumerate(resultados, start=1):
        encabezado, _, cuerpo = r.text.partition("\n")
        with st.expander(f"[{i}] {encabezado}", expanded=i <= 3):
            st.text(cuerpo)
            st.caption(f"score {r.score:.4f}")


st.title("RAG sobre las notas de parche de League of Legends")
st.caption("Parches 26.15–26.22 · chunking por habilidad · Qwen3-Embedding-0.6B + BM25 (RRF) · Claude Haiku 5.5")

if not os.getenv("ANTHROPIC_API_KEY"):
    st.warning("No hay API key: copia `.env.example` a `.env` y escribe tu clave. "
               "Sin ella se ve el retrieval, pero no se genera la respuesta.")

ejemplos = ["(escribe tu propia pregunta)"] + preguntas_ground_truth()
elegida = st.selectbox("Preguntas del ground truth", ejemplos)
pregunta = st.text_input("Pregunta (en inglés, como el corpus)",
                         value="" if elegida == ejemplos[0] else elegida)

col_opc1, col_opc2 = st.columns([1, 1])
k = col_opc1.slider("Chunks a recuperar (top-k)", 3, 10, 10)
comparar = col_opc2.checkbox("Comparar Dense contra Hybrid", value=True)

if st.button("Preguntar", type="primary", disabled=not pregunta.strip()):
    retrievers = cargar_retrievers()
    nombre_principal = "Hybrid sin cifras (el del sistema)"
    resultados = {n: r.buscar(pregunta, k=k) for n, r in retrievers.items()}

    st.subheader("Respuesta")
    if os.getenv("ANTHROPIC_API_KEY"):
        from src.generacion import responder
        with st.spinner("Claude Haiku 5.5 está respondiendo…"):
            resp = responder(pregunta, resultados[nombre_principal])
        if resp.es_negativa:
            st.info(resp.texto)
        else:
            st.markdown(resp.texto)
        st.caption(f"{resp.segundos} s · {resp.tokens_entrada} tokens de entrada, "
                   f"{resp.tokens_salida} de salida · cita los chunks {resp.citas or 'ninguno'}")
    else:
        st.write("Sin API key no se genera la respuesta.")

    st.subheader("Chunks recuperados")
    if comparar:
        izq, der = st.columns(2)
        with izq:
            st.markdown(f"**{nombre_principal}**")
            mostrar_chunks(resultados[nombre_principal])
        with der:
            st.markdown("**Dense**")
            mostrar_chunks(resultados["Dense"])
    else:
        mostrar_chunks(resultados[nombre_principal])
