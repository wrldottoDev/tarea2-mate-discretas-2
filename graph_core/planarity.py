"""Grafos planos: test de planaridad, embedding sin cruces y planarización.

1. Condición necesaria de Euler: si G es plano y V >= 3  =>  E <= 3V - 6.
2. Test exacto: algoritmo Left-Right de NetworkX (misma familia y misma
   complejidad O(V) que Boyer-Myrvold). Si falla, se extrae el certificado
   de Kuratowski: una subdivisión de K5 (5 vértices rama de grado 4) o de
   K3,3 (6 vértices rama de grado 3).
3. Si G es plano: posiciones (x, y) sin cruces (Fáry garantiza que existe un
   dibujo con aristas rectas; Chrobak-Payne lo construye en O(V)).
4. Si G no es plano: se extrae un subgrafo plano maximal y cada arista
   restante se reinserta por el camino mínimo del grafo DUAL, creando un
   NODO VIRTUAL en cada cruce. El grafo resultante (planarizado) es plano
   y se dibuja sin cruces con el paso 3.
"""
import networkx as nx


def euler_ok(V, E):
    return V < 3 or E <= 3 * V - 6


def _cross(a, b, c, d):
    """Cruce propio de los segmentos ab y cd -> (t, s, punto) o None.
    Resuelve a + t(b-a) = c + s(d-c) con productos cruz."""
    rx, ry = b[0] - a[0], b[1] - a[1]
    sx, sy = d[0] - c[0], d[1] - c[1]
    den = rx * sy - ry * sx
    if abs(den) < 1e-12:
        return None  # paralelos o colineales
    qx, qy = c[0] - a[0], c[1] - a[1]
    t = (qx * sy - qy * sx) / den
    s = (qx * ry - qy * rx) / den
    eps = 1e-9
    if eps < t < 1 - eps and eps < s < 1 - eps:
        return t, s, (a[0] + t * rx, a[1] + t * ry)
    return None


def count_crossings(pos, edges):
    """Cuenta cruces entre aristas que no comparten extremo.
    ponytail: O(E^2) por fuerza bruta; barrido de Bentley-Ottmann si E crece mucho."""
    edges = list(edges)
    total = 0
    for i, (a, b) in enumerate(edges):
        for c, d in edges[i + 1:]:
            if len({a, b, c, d}) == 4 and _cross(pos[a], pos[b], pos[c], pos[d]):
                total += 1
    return total


def _normalize(pos):
    """Escala las posiciones al cuadrado [0.05, 0.95]^2 (para la interfaz)."""
    xs = [p[0] for p in pos.values()] or [0]
    ys = [p[1] for p in pos.values()] or [0]
    w = (max(xs) - min(xs)) or 1
    h = (max(ys) - min(ys)) or 1
    return {v: (0.05 + 0.9 * (p[0] - min(xs)) / w, 0.05 + 0.9 * (p[1] - min(ys)) / h)
            for v, p in pos.items()}


def _near(p, a, b, eps):
    """¿El punto p está a distancia < eps del segmento ab?"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy or 1e-12
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return (p[0] - a[0] - t * dx) ** 2 + (p[1] - a[1] - t * dy) ** 2 < eps * eps


def _relax(G, pos, iters=150, eps=0.035):
    """Relajación de fuerzas (Fruchterman-Reingold) que PRESERVA la planaridad:
    cada movimiento de un vértice se acepta solo si sus aristas no cruzan
    ninguna otra y ningún vértice queda pegado a una arista.
    Parte de un dibujo sin cruces, así que termina en uno sin cruces.
    ponytail: O(iters * V * (V + deg * E)); se usa solo con V <= 60."""
    pos = {v: tuple(p) for v, p in pos.items()}
    nodes, edges = list(G.nodes()), list(G.edges())
    k = 0.9 / max(len(nodes), 1) ** 0.5  # distancia ideal entre vértices
    temp = 0.06

    def valid(v):
        pv = pos[v]
        for w in G[v]:
            for a, b in edges:
                if v not in (a, b) and w not in (a, b) and _cross(pv, pos[w], pos[a], pos[b]):
                    return False
            for u in nodes:
                if u not in (v, w) and _near(pos[u], pv, pos[w], eps):
                    return False
        return all(_near(pv, pos[a], pos[b], eps) is False for a, b in edges if v not in (a, b))

    for _ in range(iters):
        for v in nodes:
            x, y = pos[v]
            fx = fy = 0.0
            for w in nodes:  # repulsión entre todos los pares
                if w != v:
                    dx, dy = x - pos[w][0], y - pos[w][1]
                    d2 = dx * dx + dy * dy or 1e-9
                    fx += dx * k * k / d2
                    fy += dy * k * k / d2
            for w in G[v]:  # atracción por las aristas
                dx, dy = pos[w][0] - x, pos[w][1] - y
                d = (dx * dx + dy * dy) ** 0.5
                fx += dx * d / k
                fy += dy * d / k
            f = (fx * fx + fy * fy) ** 0.5 or 1e-9
            step = min(f, temp)
            pos[v] = (min(1.0, max(0.0, x + fx / f * step)), min(1.0, max(0.0, y + fy / f * step)))
            if not valid(v):
                pos[v] = (x, y)
        temp *= 0.98
    return pos


def plane_layout(G, pretty=True):
    """Posiciones sin cruces para un grafo plano G: Chrobak-Payne (siempre
    válido, O(V)) y, en grafos pequeños, una relajación que lo vuelve legible
    sin introducir cruces."""
    if G.number_of_nodes() == 0:
        return {}, "vacío"
    cp = _normalize({v: (float(x), float(y)) for v, (x, y) in nx.planar_layout(G).items()})
    if pretty and G.number_of_nodes() <= 60:
        return _normalize(_relax(G, cp)), "Chrobak-Payne + relajación sin cruces"
    return cp, "Chrobak-Payne"


def maximal_planar_subgraph(G):
    """Subgrafo plano maximal voraz. Un bosque generador siempre es plano, así
    que se agrega completo; el resto de aristas se agrega por bloques y, si un
    bloque rompe la planaridad, se divide a la mitad (bisección).
    ponytail: O(r log E) tests de O(V) (r = aristas rechazadas); suficiente hasta ~1000 nodos."""
    forest = [e for comp in nx.connected_components(G) for e in nx.bfs_edges(G, next(iter(comp)))]
    in_forest = {frozenset(e) for e in forest}
    rest = [e for e in G.edges() if frozenset(e) not in in_forest]
    H = nx.Graph()
    H.add_nodes_from(G.nodes())
    H.add_edges_from(forest)
    removed = []

    def add(batch):
        H.add_edges_from(batch)
        if nx.check_planarity(H)[0]:
            return
        H.remove_edges_from(batch)
        if len(batch) == 1:
            removed.append(batch[0])
            return
        mid = len(batch) // 2
        add(batch[:mid])
        add(batch[mid:])

    if rest:
        add(rest)
    return H, removed


def _faces(emb):
    """Caras de un embedding plano: cada semiarista (u, v) pertenece a una cara,
    que se recorre con next_face_half_edge hasta volver al inicio."""
    face_of = {}
    n = 0
    for u, v in emb.edges():
        if (u, v) in face_of:
            continue
        a, b = u, v
        while (a, b) not in face_of:
            face_of[(a, b)] = n
            a, b = emb.next_face_half_edge(a, b)
        n += 1
    return face_of


def _insert_edge(P, origin, u, v, virtual):
    """Inserta la arista u-v en el grafo plano P cruzando el menor número de
    aristas posible: BFS en el GRAFO DUAL (nodos = caras, una arista dual por
    cada arista primal) desde las caras que tocan u hasta las que tocan v.
    Cada arista primal cruzada se parte con un nodo virtual X_k."""
    emb = nx.check_planarity(P)[1]
    face_of = _faces(emb)
    dual = {}
    for (a, b), f in face_of.items():
        g = face_of[(b, a)]
        if f != g:
            dual.setdefault(f, []).append((g, (a, b)))
    starts = {face_of[(u, w)] for w in emb.neighbors(u)}
    goals = {face_of[(v, w)] for w in emb.neighbors(v)}
    prev = {f: None for f in starts}
    queue = list(starts)
    hit = next((f for f in queue if f in goals), None)
    while hit is None and queue:
        nxt = []
        for f in queue:
            for g, e in dual.get(f, []):
                if g not in prev:
                    prev[g] = (f, e)
                    if g in goals:
                        hit = g
                        break
                    nxt.append(g)
            if hit is not None:
                break
        queue = nxt
    crossed = []
    while prev[hit] is not None:
        hit, e = prev[hit]
        crossed.append(e)
    chain = [u]
    for a, b in reversed(crossed):
        x = f"X{len(virtual) + 1}"
        while x in P:  # evita chocar con un id real
            x += "'"
        virtual.append(x)
        o = origin.pop(frozenset((a, b)))
        P.remove_edge(a, b)
        P.add_edge(a, x)
        P.add_edge(x, b)
        origin[frozenset((a, x))] = origin[frozenset((x, b))] = o
        chain.append(x)
    chain.append(v)
    for p, q in zip(chain, chain[1:]):
        P.add_edge(p, q)
        origin[frozenset((p, q))] = (u, v)


def planarize(G, pretty=True):
    """Planarización: subgrafo plano maximal + reinserción de cada arista
    removida por el camino mínimo del dual, con nodos virtuales en los cruces.
    El resultado es plano por construcción (se verifica al final)."""
    P, removed = maximal_planar_subgraph(G)
    origin = {frozenset(e): tuple(e) for e in P.edges()}
    virtual = []
    for u, v in removed:
        _insert_edge(P, origin, u, v, virtual)
    assert nx.check_planarity(P)[0]
    pos, method = plane_layout(P, pretty)
    xs = set(virtual)
    segments = [{"source": a, "target": b, "original": list(origin[frozenset((a, b))]),
                 "rerouted": a in xs or b in xs}
                for a, b in P.edges()]
    return {"positions": pos, "segments": segments, "virtual_nodes": virtual,
            "removed_edges": [list(e) for e in removed], "layout": method,
            "planarized_is_planar": True, "planarized_V": P.number_of_nodes(),
            "planarized_E": P.number_of_edges()}


def planar_drawing(g, pretty=True, kuratowski_limit=150):
    """Punto de entrada: recibe un graph_core.Graph y devuelve el análisis
    completo de planaridad + un dibujo sin cruces (con nodos virtuales si hace falta)."""
    G = g.to_networkx()
    V, E = G.number_of_nodes(), G.number_of_edges()
    want_cert = V <= kuratowski_limit
    planar, cert = nx.check_planarity(G, counterexample=want_cert)
    out = {"planar": planar, "euler_ok": euler_ok(V, E), "euler_bound": max(3 * V - 6, 0),
           "kuratowski": None, "kuratowski_edges": [], "kuratowski_branch": []}
    if planar:
        pos, method = plane_layout(G, pretty)
        out.update(positions=pos, layout=method, virtual_nodes=[], removed_edges=[],
                   segments=[{"source": u, "target": v, "original": [u, v], "rerouted": False}
                             for u, v in G.edges()],
                   planarized_is_planar=True, planarized_V=V, planarized_E=E)
    else:
        if want_cert:
            branch = [v for v, d in cert.degree() if d > 2]
            out["kuratowski"] = "K5" if len(branch) == 5 else "K3,3"
            out["kuratowski_branch"] = branch
            out["kuratowski_edges"] = [list(e) for e in cert.edges()]
        out.update(planarize(G, pretty))
    out["crossings"] = 0  # por construcción; los tests lo verifican con count_crossings
    return out
