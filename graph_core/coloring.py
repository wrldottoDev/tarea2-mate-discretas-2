"""Coloración de vértices para asignar lotes de ejecución en paralelo.

Vértice = tarea/microservicio. Arista = conflicto (recurso compartido o
dependencia): sus extremos NO pueden ejecutarse a la vez.
Color = lote (slot de tiempo). Una coloración propia garantiza que dentro
de cada lote no hay conflictos, y el número de colores es el número de
etapas secuenciales. El mínimo posible es el número cromático chi(G).

Cotas usadas:  omega(G) <= chi(G) <= Delta(G) + 1
(omega = clique máxima, Delta = grado máximo; Brooks: chi <= Delta salvo
grafo completo o ciclo impar). Si G es plano, chi(G) <= 4.
"""
import heapq
from itertools import count


def welsh_powell(g):
    """Welsh-Powell: ordena por grado descendente y, color por color, recorre
    la lista asignando el color actual a todo vértice no adyacente a los que
    ya lo tienen.  Tiempo O(V log V + chi * (V + E)).  Usa a lo sumo Delta+1."""
    order = sorted(g.vertices(), key=lambda v: (-g.degree(v), str(v)))
    color, c = {}, 0
    while len(color) < len(order):
        members = set()  # vértices que ya recibieron el color c
        for v in order:
            if v not in color and not (g.neighbors(v) & members):
                color[v] = c
                members.add(v)
        c += 1
    return color


def dsatur(g):
    """DSatur (Brélaz, 1979): en cada paso colorea el vértice con mayor grado
    de saturación (cantidad de colores distintos entre sus vecinos), desempate
    por grado.  Le da el color libre más pequeño.
    Con un heap con entradas perezosas: O((V + E) log V)."""
    rank = {v: i for i, v in enumerate(sorted(g.vertices(), key=str))}
    sat = {v: set() for v in g.vertices()}
    heap = [(0, -g.degree(v), rank[v], v) for v in g.vertices()]
    heapq.heapify(heap)
    color = {}
    while heap:
        neg_sat, _, _, v = heapq.heappop(heap)
        if v in color or -neg_sat != len(sat[v]):
            continue  # entrada obsoleta: la saturación de v ya cambió
        c = next(i for i in count() if i not in sat[v])
        color[v] = c
        for w in g.neighbors(v):
            if w not in color and c not in sat[w]:
                sat[w].add(c)
                heapq.heappush(heap, (-len(sat[w]), -g.degree(w), rank[w], w))
    return color


def is_proper(g, coloring):
    """Una coloración es propia si ninguna arista une dos vértices del mismo color."""
    return all(coloring[u] != coloring[v] for u, v in g.edges())


def num_colors(coloring):
    return len(set(coloring.values()))


def batches(coloring):
    """Agrupa por color: lote k = tareas que pueden correr juntas en el slot k."""
    out = {}
    for v, c in coloring.items():
        out.setdefault(c, []).append(v)
    return [sorted(out[c], key=str) for c in sorted(out)]


def greedy_clique(g):
    """Clique grande por heurística voraz -> cota inferior omega(G) <= chi(G).
    O(sum deg(v)^2) en el peor caso; en grafos dispersos es casi lineal."""
    best = []
    for v in g.vertices():
        clique = [v]
        for w in sorted(g.neighbors(v), key=g.degree, reverse=True):
            if all(w in g.neighbors(u) for u in clique):
                clique.append(w)
        if len(clique) > len(best):
            best = clique
    return best


def exact_coloring(g, limit=25):
    """Coloración óptima (usa exactamente chi(G) colores) por backtracking,
    probando k = omega, omega+1, ... hasta la cota de DSatur.  Exponencial (el
    problema es NP-difícil), por eso solo se aplica si V <= limit; si no,
    devuelve None y se reporta la cota superior heurística."""
    if g.num_vertices > limit:
        return None
    best = dsatur(g)
    if g.num_vertices == 0:
        return best
    lo, hi = len(greedy_clique(g)), num_colors(best)
    order = sorted(g.vertices(), key=lambda v: (-g.degree(v), str(v)))

    def try_k(k):
        col = {}

        def bt(i, used):
            if i == len(order):
                return True
            v = order[i]
            taken = {col[w] for w in g.neighbors(v) if w in col}
            for c in range(min(used + 1, k)):  # simetría: a lo sumo un color nuevo
                if c not in taken:
                    col[v] = c
                    if bt(i + 1, max(used, c + 1)):
                        return True
                    del col[v]
            return False

        return dict(col) if bt(0, 0) else None

    for k in range(lo, hi):
        col = try_k(k)
        if col:
            return col
    return best
