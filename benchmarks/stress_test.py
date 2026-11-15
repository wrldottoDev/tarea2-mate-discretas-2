"""Pruebas de estrés con grafos aleatorios G(n, m) de 10, 100 y 1000 nodos.

Ejecutar:  python -m benchmarks.stress_test
Genera docs/bench_results.json, docs/bench_results.md y docs/bench_chart.png
"""
import json
import random
import sys
from pathlib import Path
from time import perf_counter

import networkx as nx

from graph_core import Graph, dsatur, greedy_clique, is_proper, num_colors, welsh_powell
from graph_core.coloring import exact_coloring
from graph_core.planarity import planar_drawing

OUT = Path(__file__).resolve().parent.parent / "docs"
SIZES = [int(a) for a in sys.argv[1:]] or [10, 100, 1000]
AVG_DEGREE = 3  # E = 1.5 V: densidad típica de una arquitectura de microservicios


def ms(t0):
    return round((perf_counter() - t0) * 1000, 3)


def run(n, seed=42):
    rng = random.Random(seed)
    G = nx.gnm_random_graph(n, n * AVG_DEGREE // 2, seed=seed)
    r = {"n": n, "m": G.number_of_edges()}

    t = perf_counter()
    g = Graph()
    for v in G.nodes():
        g.add_vertex(str(v))
    for u, v in G.edges():
        g.add_edge(str(u), str(v))
    r["build_ms"] = ms(t)
    mem = g.memory_bytes()
    r["mem_list_kb"], r["mem_matrix_kb"] = round(mem["lista"] / 1024, 1), round(mem["matriz"] / 1024, 1)

    vs = g.vertices()
    t = perf_counter()
    for v in vs:
        g.neighbors(v)
    r["neighbors_list_us"] = round(ms(t) * 1000 / n, 3)
    t = perf_counter()
    for v in vs:
        g.neighbors_matrix(v)
    r["neighbors_matrix_us"] = round(ms(t) * 1000 / n, 3)
    pairs = [(rng.choice(vs), rng.choice(vs)) for _ in range(10000)]
    t = perf_counter()
    for u, v in pairs:
        g.has_edge(u, v)
    r["has_edge_matrix_us"] = round(ms(t) * 1000 / len(pairs), 4)

    t = perf_counter()
    wp = welsh_powell(g)
    r["wp_ms"], r["wp_colors"] = ms(t), num_colors(wp)
    t = perf_counter()
    ds = dsatur(g)
    r["dsatur_ms"], r["dsatur_colors"] = ms(t), num_colors(ds)
    assert is_proper(g, wp) and is_proper(g, ds)
    r["clique_lb"] = len(greedy_clique(g))
    r["max_degree"] = g.max_degree()
    ex = exact_coloring(g)
    r["chi_exact"] = num_colors(ex) if ex is not None else None
    r["chi_certified"] = r["dsatur_colors"] == r["clique_lb"]  # omega = k  =>  chi = k

    t = perf_counter()
    r["planar"] = nx.check_planarity(G)[0]
    r["planarity_test_ms"] = ms(t)
    r["euler_ok"] = r["m"] <= 3 * n - 6
    t = perf_counter()
    d = planar_drawing(g, pretty=False, kuratowski_limit=0)
    r["planarize_ms"] = ms(t)
    r["removed_edges"], r["virtual_nodes"] = len(d["removed_edges"]), len(d["virtual_nodes"])
    return r


def chart(results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ns = [r["n"] for r in results]
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150)
    for key, label in [("build_ms", "Construcción (lista+matriz)"), ("wp_ms", "Welsh-Powell"),
                       ("dsatur_ms", "DSatur"), ("planarity_test_ms", "Test de planaridad"),
                       ("planarize_ms", "Planarización + embedding")]:
        a.plot(ns, [max(r[key], 1e-3) for r in results], marker="o", label=label)
    a.set(xscale="log", yscale="log", xlabel="Vértices (V)", ylabel="Tiempo (ms)", title="Tiempo por etapa")
    a.grid(alpha=.3, which="both")
    a.legend(fontsize=8)
    b.plot(ns, [r["mem_list_kb"] for r in results], marker="o", label="Lista de adyacencia O(V+E)")
    b.plot(ns, [r["mem_matrix_kb"] for r in results], marker="s", label="Matriz de adyacencia O(V²)")
    b.set(xscale="log", yscale="log", xlabel="Vértices (V)", ylabel="Memoria (KB)", title="Memoria por representación")
    b.grid(alpha=.3, which="both")
    b.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "bench_chart.png")


def table(results):
    rows = [("V", "n"), ("E", "m"), ("Construcción (ms)", "build_ms"), ("Memoria lista (KB)", "mem_list_kb"),
            ("Memoria matriz (KB)", "mem_matrix_kb"), ("Vecinos lista (µs/vértice)", "neighbors_list_us"),
            ("Vecinos matriz (µs/vértice)", "neighbors_matrix_us"), ("has_edge matriz (µs)", "has_edge_matrix_us"),
            ("Δ(G)", "max_degree"), ("Cota inferior ω (clique)", "clique_lb"), ("χ exacto (backtracking)", "chi_exact"),
            ("χ certificado (ω = k DSatur)", "chi_certified"),
            ("Welsh-Powell: colores", "wp_colors"), ("Welsh-Powell (ms)", "wp_ms"),
            ("DSatur: colores", "dsatur_colors"), ("DSatur (ms)", "dsatur_ms"), ("¿Plano?", "planar"),
            ("E ≤ 3V−6", "euler_ok"), ("Test planaridad (ms)", "planarity_test_ms"),
            ("Aristas reinsertadas", "removed_edges"), ("Nodos virtuales", "virtual_nodes"),
            ("Planarización (ms)", "planarize_ms")]
    fmt = lambda x: "—" if x is None else ("sí" if x is True else "no" if x is False else f"{x:,}".replace(",", " "))
    lines = ["| Métrica | " + " | ".join(f"V = {r['n']}" for r in results) + " |",
             "|---|" + "---:|" * len(results)]
    lines += [f"| {name} | " + " | ".join(fmt(r[k]) for r in results) + " |" for name, k in rows]
    return "\n".join(lines)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    results = []
    for n in SIZES:
        print(f"V = {n} ...", flush=True)
        results.append(run(n))
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    (OUT / "bench_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    (OUT / "bench_results.md").write_text(table(results) + "\n")
    chart(results)
    print(table(results))
