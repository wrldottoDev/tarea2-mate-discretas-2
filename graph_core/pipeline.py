"""Motor algorítmico: JSON (vértices y aristas) -> métricas, lotes y dibujo."""
from time import perf_counter

from .coloring import batches, dsatur, exact_coloring, greedy_clique, is_proper, num_colors, welsh_powell
from .graph import Graph
from .planarity import planar_drawing


def _timed(fn, *args):
    t = perf_counter()
    out = fn(*args)
    return out, round((perf_counter() - t) * 1000, 3)


def analyze(data):
    g, t_build = _timed(Graph.from_dict, data)
    wp, t_wp = _timed(welsh_powell, g)
    ds, t_ds = _timed(dsatur, g)
    opt, t_opt = _timed(exact_coloring, g)
    best, algo = (opt, "Exacto (backtracking)") if opt is not None else \
        ((ds, "DSatur") if num_colors(ds) <= num_colors(wp) else (wp, "Welsh-Powell"))
    clique = greedy_clique(g)
    drawing, t_pl = _timed(planar_drawing, g)
    lots = batches(best)
    V, E = g.num_vertices, g.num_edges
    degs = g.degrees()
    return {
        "graph": g.to_dict(),
        "stats": {
            "V": V, "E": E, "max_degree": g.max_degree(),
            "density": round(2 * E / (V * (V - 1)), 4) if V > 1 else 0,
            "degree_sum": sum(degs.values()),  # = 2E (lema del apretón de manos)
            "degrees": degs,
        },
        "coloring": {
            "welsh_powell": {"k": num_colors(wp), "ms": t_wp, "colors": wp, "proper": is_proper(g, wp)},
            "dsatur": {"k": num_colors(ds), "ms": t_ds, "colors": ds, "proper": is_proper(g, ds)},
            "exact_ms": t_opt,
            "chosen": algo,
            "colors": best,
            "chi": num_colors(best),
            # exacto si hubo backtracking, o certificado si la heurística alcanza la cota omega
            "chi_exact": opt is not None or num_colors(best) == len(clique),
            "clique": clique,
            "lower_bound": len(clique),
            "upper_bound": g.max_degree() + 1,
            "batches": lots,
            "max_parallel": max((len(b) for b in lots), default=0),
        },
        "planarity": {**drawing, "ms": t_pl},
        "build_ms": t_build,
        "code": orchestrator_code(lots),
    }


def summary(result):
    """Métricas compactas que se le entregan al LLM para redactar el reporte."""
    c, p, s = result["coloring"], result["planarity"], result["stats"]
    return {
        "vertices": s["V"], "aristas": s["E"], "grado_maximo": s["max_degree"], "densidad": s["density"],
        "numero_cromatico": c["chi"], "chi_es_exacto": c["chi_exact"], "algoritmo": c["chosen"],
        "colores_welsh_powell": c["welsh_powell"]["k"], "colores_dsatur": c["dsatur"]["k"],
        "cota_inferior_clique": c["lower_bound"], "cota_superior_delta_mas_1": c["upper_bound"],
        "lotes": c["batches"], "paralelismo_maximo": c["max_parallel"],
        "es_plano": p["planar"], "cumple_euler_E_le_3V_6": p["euler_ok"],
        "subgrafo_kuratowski": p["kuratowski"], "aristas_reenrutadas": len(p["removed_edges"]),
        "nodos_virtuales": len(p["virtual_nodes"]),
    }


def orchestrator_code(lots):
    """'Código ejecutable optimizado': un orquestador asyncio que corre los
    lotes en orden y, dentro de cada lote, todas las tareas en paralelo."""
    rows = "\n".join(f"    {lot!r},  # lote {i}" for i, lot in enumerate(lots, 1))
    return f'''"""Orquestador generado por el motor de grafos.
Cada lote es una clase de color: sus tareas no comparten recursos y corren en paralelo."""
import asyncio

LOTES = [
{rows}
]


async def ejecutar(tarea):
    print(f"  > {{tarea}}")
    await asyncio.sleep(0.2)  # aquí va la llamada real al servicio


async def main():
    for i, lote in enumerate(LOTES, 1):
        print(f"Lote {{i}}/{{len(LOTES)}}: {{len(lote)}} tareas en paralelo")
        await asyncio.gather(*(ejecutar(t) for t in lote))


if __name__ == "__main__":
    asyncio.run(main())
'''
