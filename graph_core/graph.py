"""Grafo no dirigido con doble representación: lista y matriz de adyacencia.

Ambas estructuras se mantienen sincronizadas en cada operación, de modo que
cada algoritmo puede usar la que le conviene:

    Lista de adyacencia  (dict -> set)  memoria O(V + E), vecinos en O(deg(v))
    Matriz de adyacencia (V x V, 0/1)   memoria O(V^2),   arista u-v en O(1)
"""
import json
import sys


class Graph:
    def __init__(self):
        self.adj = {}         # lista de adyacencia: vértice -> set(vecinos)
        self.index = {}       # vértice -> fila/columna en la matriz
        self.order = []       # índice -> vértice (inverso de self.index)
        self.matrix = []      # matriz de adyacencia (lista de listas 0/1)
        self.attrs = {}       # vértice -> metadatos (tipo, descripción...)
        self.edge_attrs = {}  # frozenset({u, v}) -> metadatos (recurso, tipo)

    # ---------- vértices ----------
    def add_vertex(self, v, **attrs):
        """O(V) por la matriz (nueva fila y columna); O(1) en la lista."""
        if v in self.adj:
            self.attrs[v].update(attrs)
            return
        self.adj[v] = set()
        self.attrs[v] = dict(attrs)
        self.index[v] = len(self.order)
        self.order.append(v)
        for row in self.matrix:
            row.append(0)
        self.matrix.append([0] * len(self.order))

    def remove_vertex(self, v):
        """O(V + deg(v)) en la lista, O(V^2) en la matriz (reindexar filas)."""
        for w in list(self.adj[v]):
            self.remove_edge(v, w)
        i = self.index.pop(v)
        del self.adj[v], self.attrs[v], self.order[i], self.matrix[i]
        for row in self.matrix:
            del row[i]
        for j in range(i, len(self.order)):
            self.index[self.order[j]] = j

    # ---------- aristas ----------
    def add_edge(self, u, v, **attrs):
        """O(1): un set.add en la lista y dos celdas en la matriz."""
        if u == v:
            raise ValueError(f"Lazo no permitido en grafo simple: {u}")
        self.add_vertex(u)
        self.add_vertex(v)
        self.adj[u].add(v)
        self.adj[v].add(u)
        i, j = self.index[u], self.index[v]
        self.matrix[i][j] = self.matrix[j][i] = 1
        self.edge_attrs.setdefault(frozenset((u, v)), {}).update(attrs)

    def remove_edge(self, u, v):
        self.adj[u].discard(v)
        self.adj[v].discard(u)
        i, j = self.index[u], self.index[v]
        self.matrix[i][j] = self.matrix[j][i] = 0
        self.edge_attrs.pop(frozenset((u, v)), None)

    def has_edge(self, u, v):
        """O(1) por la matriz."""
        return u in self.index and v in self.index and self.matrix[self.index[u]][self.index[v]] == 1

    # ---------- consultas ----------
    def vertices(self):
        return list(self.order)

    def edges(self):
        """Cada arista una sola vez, recorriendo la lista: O(V + E log deg).
        (Se ordenan los vecinos por índice para que el resultado sea determinista.)"""
        seen, out = set(), []
        for u in self.order:
            for v in sorted(self.adj[u], key=self.index.__getitem__):
                if v not in seen:
                    out.append((u, v))
            seen.add(u)
        return out

    def neighbors(self, v):
        """Lista: O(deg(v))."""
        return self.adj[v]

    def neighbors_matrix(self, v):
        """Matriz: hay que recorrer la fila completa, O(V)."""
        row = self.matrix[self.index[v]]
        return {self.order[j] for j, bit in enumerate(row) if bit}

    def degree(self, v):
        return len(self.adj[v])

    def degrees(self):
        return {v: len(self.adj[v]) for v in self.order}

    def max_degree(self):
        return max((len(s) for s in self.adj.values()), default=0)

    @property
    def num_vertices(self):
        return len(self.order)

    @property
    def num_edges(self):
        return sum(len(s) for s in self.adj.values()) // 2  # lema del apretón de manos

    def memory_bytes(self):
        """Tamaño aproximado en bytes de cada representación."""
        lst = sys.getsizeof(self.adj) + sum(sys.getsizeof(s) for s in self.adj.values())
        mat = sys.getsizeof(self.matrix) + sum(sys.getsizeof(r) for r in self.matrix)
        return {"lista": lst, "matriz": mat}

    # ---------- exportación ----------
    def to_dict(self):
        return {
            "nodes": [{"id": v, **self.attrs[v]} for v in self.order],
            "edges": [{"source": u, "target": v, **self.edge_attrs.get(frozenset((u, v)), {})}
                      for u, v in self.edges()],
        }

    def to_json(self, **kw):
        return json.dumps(self.to_dict(), ensure_ascii=False, **kw)

    @classmethod
    def from_dict(cls, data):
        g = cls()
        for n in data["nodes"]:
            g.add_vertex(n["id"], **{k: val for k, val in n.items() if k != "id"})
        for e in data["edges"]:
            g.add_edge(e["source"], e["target"],
                       **{k: val for k, val in e.items() if k not in ("source", "target")})
        return g

    def to_networkx(self):
        import networkx as nx
        G = nx.Graph()
        G.add_nodes_from((v, self.attrs[v]) for v in self.order)
        G.add_edges_from((u, v, self.edge_attrs.get(frozenset((u, v)), {})) for u, v in self.edges())
        return G

    def __repr__(self):
        return f"Graph(V={self.num_vertices}, E={self.num_edges})"
