#!/usr/bin/env python3
"""
Diagnóstico visual de datos.gob.es con Playwright.
Guarda screenshot + HTML para inspeccionar por qué no aparecen resultados.
"""

import time
from pathlib import Path
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit("❌ Instala Playwright")


BASE_URL = "https://datos.gob.es/es/catalogo"
QUERY = "empleo juvenil"
OUTPUT_DIR = Path(__file__).parent.parent / "entregables" / "diagnostico_dge"
TIMEOUT_MS = 60_000


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}?q={quote(QUERY)}"

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) "
                "Gecko/20100101 Firefox/140.0"
            ),
            locale="es-ES",
            timezone_id="Europe/Madrid",
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        page = context.new_page()

        print(f"Navegando a {url}...")
        page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
        time.sleep(10)

        html_path = OUTPUT_DIR / "page.html"
        screenshot_path = OUTPUT_DIR / "page.png"
        html_path.write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(screenshot_path), full_page=True)

        # Intentar detectar textos típicos de resultados
        page_text = page.inner_text("body")
        snippets = [
            "resultados" in page_text.lower(),
            "dataset" in page_text.lower(),
            "buscar" in page_text.lower(),
            "no se han encontrado" in page_text.lower(),
        ]

        print(f"HTML guardado: {html_path}")
        print(f"Screenshot guardado: {screenshot_path}")
        print(f"Tamaño HTML: {len(page.content())} caracteres")
        print(f"Detectado 'resultados': {snippets[0]}")
        print(f"Detectado 'dataset': {snippets[1]}")
        print(f"Detectado 'buscar': {snippets[2]}")
        print(f"Detectado 'no se han encontrado': {snippets[3]}")

        # Extraer todos los textos largos (posibles títulos de datasets)
        elements = page.query_selector_all("*")
        texts = []
        for el in elements:
            try:
                text = el.inner_text().strip()
                if 20 < len(text) < 150 and text not in texts:
                    texts.append(text)
            except Exception:
                pass
        print("\n--- Textos largos encontrados (primeros 30) ---")
        for i, t in enumerate(texts[:30], 1):
            print(f"{i:2}. {t[:120]}")

        browser.close()


if __name__ == "__main__":
    main()
