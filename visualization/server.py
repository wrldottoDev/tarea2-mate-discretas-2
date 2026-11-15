"""Dashboard web (solo biblioteca estándar).  Ejecutar:  python -m visualization.server
Abre http://localhost:8000
"""
import json
import sys
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import perf_counter

from ai_agent import MODEL, clean_graph, parse_requirement, provider, write_report
from graph_core import analyze, summary

ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parent / "docs"
EXAMPLES = json.loads((ROOT / "examples.json").read_text())


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT / "static"), **kw)

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/config":
            return self._json({"provider": provider(), "model": MODEL, "examples": EXAMPLES})
        if self.path == "/api/bench":
            f = DOCS / "bench_results.json"
            return self._json(json.loads(f.read_text()) if f.exists() else [])
        if self.path == "/bench_chart.png":
            self.directory = str(DOCS)
        return super().do_GET()

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            t = perf_counter()
            if self.path == "/api/parse":
                out = {"graph": parse_requirement(body["text"][:4000])}
            elif self.path == "/api/analyze":
                g = clean_graph(body["graph"])
                out = analyze(g)
                out["summary"] = summary(out)
            elif self.path == "/api/report":
                out = {"report": write_report(body["text"][:4000], body["summary"])}
            else:
                return self._json({"error": "ruta desconocida"}, 404)
            out["seconds"] = round(perf_counter() - t, 2)
            self._json(out)
        except Exception as e:  # el error se muestra en la interfaz
            traceback.print_exc()
            self._json({"error": f"{type(e).__name__}: {e}"}, 500)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Dashboard en http://localhost:{port}  (LLM: {provider()} / {MODEL})")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
