# GrafoOps — Motor IA de Planificación y Orquestación basado en Grafos

Tarea 2 · Matemática Discreta II (FUN-03) · Universidad CENFOTEC · C3-2026

Un agente LLM convierte un requerimiento en lenguaje natural en un **grafo de recursos**
(JSON con vértices y aristas). Sobre ese grafo se ejecutan algoritmos deterministas:

- **Coloración de vértices** (Welsh-Powell, DSatur y óptimo por backtracking): cada color es un
  lote de ejecución en paralelo sin conflictos; el número de lotes es el número cromático χ(G).
- **Planaridad** (Euler, test Left-Right/Boyer-Myrvold, certificado de Kuratowski K5/K3,3):
  si el grafo es plano se calcula un embedding sin cruces; si no, se planariza insertando
  **nodos virtuales** por caminos mínimos del grafo dual.
- El LLM interpreta las métricas y redacta un **reporte técnico** con la infraestructura mínima.

```
[Requerimiento en lenguaje natural]
            │
            ▼
[ai_agent: LLM + Structured Output] ──► JSON (vértices y aristas) ──► validación
            │
            ▼
[graph_core: motor algorítmico]
 ├─ 1. Graph: lista + matriz de adyacencia
 ├─ 2. Planaridad: Euler · LR/Boyer-Myrvold · Kuratowski · embedding · nodos virtuales
 └─ 3. Coloración: Welsh-Powell · DSatur · χ(G) exacto
            │
            ▼
[visualization: dashboard web] + reporte IA + orquestador asyncio generado
```

## Estructura

| Carpeta | Contenido |
|---|---|
| `graph_core/` | `graph.py` (clase `Graph`), `coloring.py`, `planarity.py`, `pipeline.py` |
| `ai_agent/` | `prompts.py` (prompts + esquema JSON), `agent.py` (llamadas al LLM y validación) |
| `visualization/` | `server.py` (HTTP, solo biblioteca estándar) y `static/index.html` (dashboard) |
| `benchmarks/` | `stress_test.py`: pruebas de estrés con 10, 100 y 1000 nodos |
| `tests/` | pruebas del núcleo matemático |
| `docs/` | informe PDF, resultados y gráfico de las pruebas de estrés |

## Uso

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m visualization.server        # dashboard en http://localhost:8000
python -m tests.test_graph_core       # pruebas
python -m benchmarks.stress_test      # pruebas de estrés (≈3 min por el caso de 1000 nodos)
```

### Proveedor del LLM

Se elige con `LLM_PROVIDER` o automáticamente en este orden:

| Proveedor | Requisito |
|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` (SDK oficial, modelo `claude-opus-5-5`, structured outputs) |
| `claude-cli` | Claude Code instalado (`claude -p --json-schema`) |
| `offline` | nada: parser por palabras clave para probar sin red |

## Complejidad (resumen)

| Operación | Lista de adyacencia | Matriz de adyacencia |
|---|---|---|
| Memoria | O(V + E) | O(V²) |
| Agregar vértice | O(1) | O(V) |
| Agregar / quitar arista | O(1) | O(1) |
| ¿Existe u–v? | O(1) esperado (set) | O(1) |
| Vecinos de v | O(deg v) | O(V) |

| Algoritmo | Tiempo |
|---|---|
| Welsh-Powell | O(V log V + χ·(V + E)) |
| DSatur (heap) | O((V + E) log V) |
| χ exacto (backtracking) | exponencial, solo V ≤ 25 |
| Test de planaridad (LR / Boyer-Myrvold) | O(V) |
| Embedding Chrobak-Payne | O(V) |
| Subgrafo plano maximal | O(r · log E · V) |
| Inserción por grafo dual | O(r · (V + cruces)) |
