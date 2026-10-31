#!/usr/bin/env python3
"""
Obtiene los top 10 resultados de búsqueda de datos.gob.es (web real)
para el conjunto de queries de evaluación.

Uso:
    source venv/bin/activate
    python search_datosgobes_web.py \
        --input ../entregables/dataset_evaluacion.jsonl \
        --output ../entregables/datosgobes_search_results.jsonl

Salida: JSONL con una línea por query:
    {"id": "...", "query": "...", "titles": [...], "status": "ok", ...}
"""

import json
import argparse
import time
from pathlib import Path
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    raise SystemExit("❌ Instala Playwright: pip install playwright && playwright install firefox")


BASE_URL = "https://datos.gob.es/es/catalogo"
SELECTOR_TITULOS = ".dge-list__title.dataset-heading"
TIMEOUT_GOTO_MS = 60_000
TIMEOUT_SELECTOR_MS = 20_000
PAUSA_ENTRE_QUERIES_SEC = 2


def cargar_queries(path: Path) -> list[dict]:
    queries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line))
    return queries


def buscar_datosgobes(query: str, page, context) -> dict:
    url = f"{BASE_URL}?q={quote(query)}"
    result = {
        "query": query,
        "url": url,
        "status": "unknown",
        "titles": [],
        "n_total": 0,
        "error": None,
        "elapsed_sec": 0.0,
    }

    start = time.time()
    try:
        try:
            page.goto(url, wait_until="networkidle", timeout=TIMEOUT_GOTO_MS)
        except PWTimeout:
            page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_GOTO_MS)

        try:
            page.wait_for_selector(SELECTOR_TITULOS, timeout=TIMEOUT_SELECTOR_MS)
        except PWTimeout:
            pass

        elements = page.query_selector_all(SELECTOR_TITULOS)
        titles = [el.inner_text().strip() for el in elements if el.inner_text().strip()]

        # Extraer contador total de resultados si está disponible
        total_text = ""
        total_el = page.query_selector(".search-results .total-results, .resultados-count, .dge-list__counter")
        if total_el:
            total_text = total_el.inner_text().strip()

        result["titles"] = titles[:10]
        result["n_total"] = len(titles)
        result["total_text"] = total_text
        result["status"] = "ok" if titles else "no_titles"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    result["elapsed_sec"] = round(time.time() - start, 2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", type=str, default="../entregables/dataset_evaluacion.jsonl")
    parser.add_argument("--output", "-o", type=str, default="../entregables/datosgobes_search_results.jsonl")
    parser.add_argument("--limit", "-l", type=int, default=None)
    parser.add_argument("--resume", "-r", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    queries = cargar_queries(input_path)
    if args.limit:
        queries = queries[:args.limit]

    # Reanudar si existe
    procesados = {}
    if args.resume and output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    procesados[obj["id"]] = obj
        print(f"🔄 Reanudando: {len(procesados)} queries ya procesadas")
        queries = [q for q in queries if q["id"] not in procesados]

    if not queries:
        print("✅ No hay queries pendientes")
        return

    print(f"🔍 Procesando {len(queries)} queries contra {BASE_URL}...")

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

        with open(output_path, "a" if args.resume else "w", encoding="utf-8") as out_f:
            for i, q in enumerate(queries, 1):
                print(f"   [{i}/{len(queries)}] {q['id']}: {q['query'][:50]}...", end=" ", flush=True)
                res = buscar_datosgobes(q["query"], page, context)
                res["id"] = q["id"]
                res["categoria"] = q.get("categoria", "unknown")
                res["dificultad"] = q.get("dificultad", "unknown")

                status_icon = "✅" if res["status"] == "ok" and len(res["titles"]) >= 10 else "⚠️" if res["status"] == "ok" else "❌"
                print(f"{status_icon} {len(res['titles'])} títulos ({res['elapsed_sec']}s)")

                out_f.write(json.dumps(res, ensure_ascii=False) + "\n")
                out_f.flush()

                if i < len(queries):
                    time.sleep(PAUSA_ENTRE_QUERIES_SEC)

        browser.close()

    print(f"\n📁 Resultados guardados en: {output_path}")


if __name__ == "__main__":
    main()
