#!/usr/bin/env python3
"""
Script piloto para comprobar si Playwright puede superar Incapsula
y extraer resultados de búsqueda de datos.gob.es.

Uso:
    source venv/bin/activate
    python probe_datosgobes_web.py

Salida:
    ../entregables/probe_datosgobes_web_resultado.json
"""

import json
import time
from pathlib import Path
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    raise SystemExit("❌ Instala Playwright: pip install playwright && playwright install firefox")


BASE_URL = "https://datos.gob.es/es/catalogo"
QUERIES = [
    "empleo juvenil",
    "paro registrado por comunidades",
    "brecha salarial género",
]
OUTPUT = Path(__file__).parent.parent / "entregables" / "probe_datosgobes_web_resultado.json"
TIMEOUT_MS = 30_000


def fetch_results(query: str, page) -> dict:
    """Navega a la página de resultados y extrae títulos."""
    url = f"{BASE_URL}?q={quote(query)}"
    print(f"\n🔍 Query: {query}")
    print(f"   URL: {url}")

    result = {
        "query": query,
        "url": url,
        "status": "unknown",
        "titles": [],
        "error": None,
        "has_incapsula": False,
        "elapsed_sec": 0.0,
    }

    start = time.time()
    try:
        # Cargar hasta que la red esté inactiva para que JS renderice resultados
        try:
            page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
        except PWTimeout:
            page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

        html = page.content()
        result["has_incapsula"] = "_Incapsula_Resource" in html or "incapsula" in html.lower()

        # Si hay Incapsula, intentar esperar un poco más
        if result["has_incapsula"]:
            print("   ⚠️  Detectada página de Incapsula, esperando...")
            time.sleep(10)
            html = page.content()
            result["has_incapsula"] = "_Incapsula_Resource" in html

        # Esperar a que aparezcan los resultados (renderizado JS)
        try:
            page.wait_for_selector(".dataset-content", timeout=20_000)
        except PWTimeout:
            pass  # seguimos intentando extraer lo que haya

        # Intento 1: selector específico de datos.gob.es
        selectors = [
            ".dge-list__title.dataset-heading",
            ".dataset-content .dge-list__title",
            ".dataset-heading",
        ]

        titles = []
        for selector in selectors:
            elements = page.query_selector_all(selector)
            titles = [el.inner_text().strip() for el in elements if el.inner_text().strip()]
            if titles:
                print(f"   ✅ Selector encontrado: {selector} ({len(titles)} títulos)")
                break

        # Intento 2: fallback genérico por enlaces del catálogo
        if not titles:
            all_links = page.query_selector_all("a")
            candidates = []
            for a in all_links:
                href = a.get_attribute("href") or ""
                text = a.inner_text().strip()
                if text and ("catalogo" in href or "/dataset/" in href):
                    candidates.append(text)
            if candidates:
                print(f"   ℹ️  Usando enlaces con 'catalogo' en href ({len(candidates)} candidatos)")
                titles = candidates[:15]

        result["titles"] = titles[:10]
        result["status"] = "ok" if titles else "no_titles"
        if not titles and result["has_incapsula"]:
            result["status"] = "incapsula_blocked"

    except PWTimeout as e:
        result["status"] = "timeout"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    result["elapsed_sec"] = round(time.time() - start, 2)
    print(f"   Status: {result['status']} | Títulos: {len(result['titles'])} | Tiempo: {result['elapsed_sec']}s")
    for i, t in enumerate(result["titles"][:5], 1):
        print(f"      {i}. {t[:100]}")

    return result


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    results = []
    with sync_playwright() as p:
        # Usar Firefox con user-agent real y viewport real
        browser = p.firefox.launch(
            headless=True,
            args=["--width=1920", "--height=1080"],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) "
                "Gecko/20100101 Firefox/140.0"
            ),
            locale="es-ES",
            timezone_id="Europe/Madrid",
        )

        # Ocultar webdriver
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = context.new_page()

        for query in QUERIES:
            result = fetch_results(query, page)
            results.append(result)
            time.sleep(3)  # pausa entre queries

        browser.close()

    output_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "base_url": BASE_URL,
        "n_queries": len(results),
        "results": results,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n📁 Resultado guardado en: {OUTPUT}")
    print(f"   Resumen: {sum(1 for r in results if r['status']=='ok')} ok / {len(results)} queries")


if __name__ == "__main__":
    main()
