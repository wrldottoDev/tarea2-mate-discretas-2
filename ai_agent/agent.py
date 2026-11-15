"""Agente LLM: lenguaje natural -> JSON del grafo, y métricas -> reporte técnico.

Proveedor (variable LLM_PROVIDER, o detección automática en este orden):
  anthropic   API de Claude con el SDK oficial (requiere ANTHROPIC_API_KEY)
  claude-cli  Claude Code en modo headless (`claude -p --json-schema`)
  offline     parser por palabras clave, sin red (para pruebas y respaldo)
"""
import json
import os
import re
import shutil
import subprocess

from .prompts import GRAPH_SCHEMA, NODE_TYPES, PARSER_SYSTEM, REPORT_SYSTEM

MODEL = os.environ.get("LLM_MODEL", "claude-opus-5-5")


def provider():
    if os.environ.get("LLM_PROVIDER"):
        return os.environ["LLM_PROVIDER"]
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if shutil.which("claude"):
        return "claude-cli"
    return "offline"


def _ask_api(system, user, schema, effort):
    import anthropic
    output_config = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    resp = anthropic.Anthropic().beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config=output_config,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # si el modelo rechaza, el servidor reintenta con otro modelo
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("El modelo rechazó la solicitud")
    text = "".join(b.text for b in resp.content if b.type == "text")
    return json.loads(text) if schema else text


def _ask_cli(system, user, schema, effort):
    cmd = ["claude", "-p", "--system-prompt", system, "--model", MODEL, "--effort", effort,
           "--output-format", "json", "--tools", "", "--strict-mcp-config", "--setting-sources", "",
           "--disable-slash-commands", "--no-session-persistence"]
    if schema:
        cmd += ["--json-schema", json.dumps(schema)]
    out = subprocess.run(cmd, input=user, capture_output=True, text=True, timeout=300)
    if out.returncode:
        raise RuntimeError(out.stderr.strip() or out.stdout.strip())
    data = json.loads(out.stdout)
    if data.get("is_error"):
        raise RuntimeError(data.get("result"))
    return data["structured_output"] if schema else data["result"]


def _ask(system, user, schema=None, effort="low"):
    fn = {"anthropic": _ask_api, "claude-cli": _ask_cli}[provider()]
    return fn(system, user, schema, effort)


def clean_graph(data):
    """Valida la salida del LLM (frontera de confianza): ids únicos, aristas
    entre nodos existentes, sin lazos ni duplicados."""
    nodes, ids, warnings = [], set(), []
    for n in data.get("nodes", []):
        nid = re.sub(r"\W+", "_", str(n.get("id", "")).strip()).strip("_").lower()
        if not nid or nid in ids:
            warnings.append(f"Nodo descartado (id vacío o repetido): {n.get('id')!r}")
            continue
        ids.add(nid)
        nodes.append({"id": nid, "label": str(n.get("label") or nid)[:40],
                      "type": n.get("type") if n.get("type") in NODE_TYPES else "service",
                      "description": str(n.get("description", ""))[:200]})
    edges, pairs = [], set()
    for e in data.get("edges", []):
        u = re.sub(r"\W+", "_", str(e.get("source", ""))).strip("_").lower()
        v = re.sub(r"\W+", "_", str(e.get("target", ""))).strip("_").lower()
        key = frozenset((u, v))
        if key in pairs:
            continue  # arista repetida (p. ej. dependencia y conflicto a la vez): basta una
        if u not in ids or v not in ids or u == v:
            warnings.append(f"Arista descartada (nodo inexistente o lazo): {u} - {v}")
            continue
        pairs.add(key)
        edges.append({"source": u, "target": v,
                      "kind": e.get("kind") if e.get("kind") in ("dependency", "conflict") else "dependency",
                      "resource": str(e.get("resource", ""))[:60]})
    return {"title": str(data.get("title", "Arquitectura"))[:80], "nodes": nodes, "edges": edges,
            "warnings": warnings}


def parse_requirement(text):
    """Lenguaje natural -> grafo de recursos (JSON validado)."""
    if provider() == "offline":
        return clean_graph(_offline_parse(text))
    return clean_graph(_ask(PARSER_SYSTEM, f"Requerimiento:\n{text}", GRAPH_SCHEMA, effort="low"))


def write_report(text, metrics):
    """Métricas deterministas (chi(G), planaridad...) -> reporte técnico en Markdown."""
    if provider() == "offline":
        return _offline_report(metrics)
    user = f"Requerimiento:\n{text}\n\nMétricas calculadas:\n{json.dumps(metrics, ensure_ascii=False, indent=1)}"
    return _ask(REPORT_SYSTEM, user, effort="medium")


# ---------------- respaldo sin LLM ----------------
_KEYWORDS = [
    (r"pago|payment|cobro", "pagos", "Pagos", "service"),
    (r"inventario|stock", "inventario", "Inventario", "service"),
    (r"notifica|correo|email|sms|push", "notificaciones", "Notificaciones", "service"),
    (r"usuario|login|auth|cuenta", "auth", "Autenticación", "service"),
    (r"cat[aá]logo|producto", "catalogo", "Catálogo", "service"),
    (r"carrito", "carrito", "Carrito", "service"),
    (r"pedido|orden|compra", "pedidos", "Pedidos", "service"),
    (r"env[ií]o|log[ií]stica", "envios", "Envíos", "service"),
    (r"b[uú]squeda|search", "busqueda", "Búsqueda", "service"),
    (r"recomend", "recomendaciones", "Recomendaciones", "worker"),
    (r"report|anal[ií]tica|m[eé]trica", "analitica", "Analítica", "worker"),
]


def _offline_parse(text):
    t = text.lower()
    svc = [(i, l, ty) for rx, i, l, ty in _KEYWORDS if re.search(rx, t)] or [(i, l, ty) for _, i, l, ty in _KEYWORDS[:4]]
    nodes = [{"id": "api_gateway", "label": "API Gateway", "type": "gateway", "description": "Entrada única"},
             {"id": "db", "label": "Base de datos", "type": "database", "description": "PostgreSQL"},
             {"id": "bus", "label": "Bus de eventos", "type": "queue", "description": "Kafka"}]
    nodes += [{"id": i, "label": l, "type": ty, "description": ""} for i, l, ty in svc]
    edges = []
    for k, (i, _, _) in enumerate(svc):
        edges.append({"source": "api_gateway", "target": i, "kind": "dependency", "resource": "HTTP"})
        edges.append({"source": i, "target": "db" if k % 2 == 0 else "bus", "kind": "dependency",
                      "resource": "tabla " + i if k % 2 == 0 else "topic " + i})
        if k:
            edges.append({"source": svc[k - 1][0], "target": i, "kind": "conflict", "resource": "pool de conexiones"})
    return {"title": "Arquitectura (modo offline)", "nodes": nodes, "edges": edges}


def _offline_report(m):
    lotes = "\n".join(f"- Lote {i}: {', '.join(b)}" for i, b in enumerate(m["lotes"], 1))
    plano = ("El grafo es plano: el diagrama se dibuja sin cruces." if m["es_plano"] else
             f"No es plano (subgrafo {m['subgrafo_kuratowski'] or 'de Kuratowski'}); se agregaron "
             f"{m['nodos_virtuales']} nodos virtuales para dibujarlo sin cruces.")
    return (f"### Diagnóstico\n{m['vertices']} componentes y {m['aristas']} conflictos/dependencias.\n\n"
            f"### Lotes de ejecución\nχ(G) = {m['numero_cromatico']} "
            f"({m['cota_inferior_clique']} ≤ χ ≤ {m['cota_superior_delta_mas_1']}).\n{lotes}\n\n"
            f"### Infraestructura mínima recomendada\n{m['numero_cromatico']} slots secuenciales y "
            f"{m['paralelismo_maximo']} workers concurrentes.\n\n### Diagrama de arquitectura\n{plano}\n\n"
            "### Riesgos\nReporte generado sin LLM (modo offline).")
