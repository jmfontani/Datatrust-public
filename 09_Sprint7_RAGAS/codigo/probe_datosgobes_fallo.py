#!/usr/bin/env python3
"""
Diagnóstico de queries con 0 títulos en datos.gob.es.
"""

import time
from pathlib import Path
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit("❌ Instala Playwright")


QUERIES = [
    "contratos temporales vs indefinidos",
    "pirámide poblacional Andalucía",
    "consumo agua embalses",
    "abandono escolar temprano",
]
OUTPUT_DIR = Path(__file__).parent.parent / "entregables" / "diagnostico_fallos_dge"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

        for query in QUERIES:
            url = f"https://datos.gob.es/es/catalogo?q={quote(query)}"
            print(f"\n🔍 {query}")
            page.goto(url, wait_until="networkidle", timeout=60_000)
            time.sleep(5)

            html_path = OUTPUT_DIR / f"{query.replace(' ', '_').lower()}.html"
            screenshot_path = OUTPUT_DIR / f"{query.replace(' ', '_').lower()}.png"
            html_path.write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(screenshot_path), full_page=True)

            body_text = page.inner_text("body").lower()
            print(f"   HTML: {html_path}")
            print(f"   Screenshot: {screenshot_path}")
            print(f"   'no se han encontrado': {'no se han encontrado' in body_text}")
            print(f"   'conjuntos de datos': {'conjuntos de datos' in body_text}")
            print(f"   '0 resultados': {'0 resultados' in body_text or '(0)' in body_text}")

        browser.close()


if __name__ == "__main__":
    main()
