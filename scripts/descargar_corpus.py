"""Descarga las notas oficiales de los parches 26.15 a 26.22 de League of Legends.

Por cada parche guarda en data/raw/:
  - patch-26-XX.pdf   página renderizada e impresa a PDF (entrada del pipeline)
  - patch-26-XX.html  HTML completo, como respaldo para comparar el parsing

Uso:
    .venv/bin/python scripts/descargar_corpus.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

PARCHES = range(15, 23)  # 26.15 ... 26.22
URL = "https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-{n}-notes/"
DESTINO = Path(__file__).resolve().parent.parent / "data" / "raw"


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        for n in PARCHES:
            url = URL.format(n=n)
            resp = page.goto(url, wait_until="networkidle", timeout=60_000)
            if resp is None or resp.status != 200:
                print(f"26.{n}: ERROR {resp.status if resp else 'sin respuesta'} en {url}")
                continue
            # Desplazarse hasta el final para que carguen las imágenes diferidas.
            page.evaluate(
                """async () => {
                    for (let y = 0; y < document.body.scrollHeight; y += 800) {
                        window.scrollTo(0, y);
                        await new Promise(r => setTimeout(r, 150));
                    }
                    window.scrollTo(0, 0);
                }"""
            )
            page.wait_for_timeout(1000)
            base = DESTINO / f"patch-26-{n}"
            base.with_suffix(".html").write_text(page.content(), encoding="utf-8")
            page.pdf(path=str(base.with_suffix(".pdf")), format="A4", print_background=True)
            print(f"26.{n}: ok -> {base.name}.pdf / .html")
        browser.close()


if __name__ == "__main__":
    main()
