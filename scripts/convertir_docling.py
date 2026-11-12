"""Paso 1 del parsing: convierte cada PDF de data/raw/ con Docling.

Guarda el documento completo de Docling (estructura, etiquetas y posiciones) en
data/interim/patch-26-XX.docling.json. El paso 2 (scripts/parsear_corpus.py)
parte de esos JSON, así no hay que volver a correr Docling cada vez que se
ajustan las reglas de limpieza.

OCR desactivado: los PDF se generan desde el navegador y ya traen capa de texto.
Con OCR, Docling intentaba leer los íconos y metía caracteres basura.

Uso:
    .venv/bin/python scripts/convertir_docling.py
"""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "data" / "raw"
DESTINO = RAIZ / "data" / "interim"


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    opciones = PdfPipelineOptions(do_ocr=False)
    conversor = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opciones)}
    )
    for pdf in sorted(ORIGEN.glob("patch-26-*.pdf")):
        doc = conversor.convert(pdf).document
        salida = DESTINO / f"{pdf.stem}.docling.json"
        doc.save_as_json(salida)
        print(f"{pdf.name} -> {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
