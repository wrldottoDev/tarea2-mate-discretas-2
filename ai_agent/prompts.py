"""Prompts y esquema JSON (Structured Output) del agente."""

NODE_TYPES = ["gateway", "frontend", "service", "worker", "database", "cache", "queue", "external"]

GRAPH_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "type": {"type": "string", "enum": NODE_TYPES},
                    "description": {"type": "string"},
                },
                "required": ["id", "label", "type", "description"],
                "additionalProperties": False,
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "kind": {"type": "string", "enum": ["dependency", "conflict"]},
                    "resource": {"type": "string"},
                },
                "required": ["source", "target", "kind", "resource"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "nodes", "edges"],
    "additionalProperties": False,
}

PARSER_SYSTEM = """Eres un arquitecto de software. Conviertes un requerimiento en lenguaje natural en un GRAFO DE RECURSOS no dirigido que luego procesan algoritmos deterministas de coloración y planaridad.

Reglas:
- nodes: entre 6 y 16 componentes (gateway, frontend, service, worker, database, cache, queue, external). id corto en snake_case; label legible en español; description de una línea.
- edges: una arista une dos componentes que NO pueden ejecutarse o desplegarse en el mismo lote.
  · kind = "dependency" si uno llama, lee o escribe al otro.
  · kind = "conflict" si compiten por un recurso exclusivo (misma tabla con bloqueos, mismo límite de tasa de una API externa, misma cola con consumidor exclusivo, misma ventana de migración).
  · resource = nombre concreto del recurso o canal compartido.
- Sin lazos, sin aristas duplicadas; toda arista referencia ids existentes.
- Modela solo lo que el requerimiento pide o implica claramente."""

REPORT_SYSTEM = """Eres un ingeniero de plataforma. Recibes un requerimiento y las métricas que calcularon algoritmos deterministas sobre su grafo de recursos (coloración de vértices y planaridad). No recalcules ni contradigas las métricas: interprétalas.

Escribe un reporte técnico en español, en Markdown, de máximo 220 palabras, con estas secciones:
### Diagnóstico
### Lotes de ejecución
(explica qué significa χ(G) aquí: número mínimo de lotes/slots sin conflictos; menciona las cotas ω ≤ χ ≤ Δ+1)
### Infraestructura mínima recomendada
(número de slots = χ(G), workers concurrentes = tamaño del lote más grande, y qué separar en nodos distintos)
### Diagrama de arquitectura
(si es plano: diagrama sin cruces; si no: qué subgrafo de Kuratowski lo impide y cuántos nodos virtuales/buses se agregaron)
### Riesgos
Sé concreto y usa los nombres de los componentes."""
