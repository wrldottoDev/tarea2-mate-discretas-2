"""Pruebas del núcleo matemático.  Ejecutar:  python -m tests.test_graph_core"""
import random

import networkx as nx

from graph_core import Graph, analyze, count_crossings, dsatur, exact_coloring, is_proper, num_colors, welsh_powell


def from_nx(G):
    g = Graph()
    for v in G.nodes():
        g.add_vertex(str(v))
    for u, v in G.edges():
        g.add_edge(str(u), str(v))
    return g


def test_structure():
    g = from_nx(nx.petersen_graph())
    assert g.num_vertices == 10 and g.num_edges == 15
    assert sum(g.degrees().values()) == 2 * g.num_edges          # apretón de manos
    assert all(g.neighbors(v) == g.neighbors_matrix(v) for v in g.vertices())  # lista == matriz
    g.remove_vertex("0")
    assert g.num_vertices == 9 and g.num_edges == 12
    assert len(g.matrix) == 9 and all(len(r) == 9 for r in g.matrix)
    assert all(g.neighbors(v) == g.neighbors_matrix(v) for v in g.vertices())
    g.remove_edge("1", "2")
    assert not g.has_edge("1", "2") and not g.has_edge("2", "1")
    assert Graph.from_dict(g.to_dict()).num_edges == g.num_edges  # ida y vuelta JSON
    assert g.to_networkx().number_of_edges() == g.num_edges


def test_coloring():
    rng = random.Random(1)
    for _ in range(30):
        g = from_nx(nx.gnp_random_graph(rng.randint(5, 60), rng.random() * 0.4, seed=rng.randint(0, 9999)))
        for col in (welsh_powell(g), dsatur(g)):
            assert len(col) == g.num_vertices and is_proper(g, col)
            assert num_colors(col) <= g.max_degree() + 1             # cota Delta + 1
    cases = {"K5": (nx.complete_graph(5), 5), "C5": (nx.cycle_graph(5), 3), "C6": (nx.cycle_graph(6), 2),
             "K3,3": (nx.complete_bipartite_graph(3, 3), 2), "Petersen": (nx.petersen_graph(), 3)}
    for name, (G, chi) in cases.items():
        col = exact_coloring(from_nx(G))
        assert is_proper(from_nx(G), col) and num_colors(col) == chi, name


def test_planarity():
    r = analyze(from_nx(nx.complete_graph(5)).to_dict())["planarity"]
    assert not r["planar"] and r["kuratowski"] == "K5" and r["virtual_nodes"]
    r = analyze(from_nx(nx.complete_bipartite_graph(3, 3)).to_dict())["planarity"]
    assert not r["planar"] and r["kuratowski"] == "K3,3"
    for G in (nx.petersen_graph(), nx.gnp_random_graph(25, 0.3, seed=3), nx.complete_graph(7)):
        r = analyze(from_nx(G).to_dict())["planarity"]
        P = nx.Graph((s["source"], s["target"]) for s in r["segments"])
        assert nx.check_planarity(P)[0]                              # planarizado es plano
        assert count_crossings(r["positions"], P.edges()) == 0      # y el dibujo no tiene cruces
    for G in (nx.grid_2d_graph(4, 4), nx.wheel_graph(9), nx.octahedral_graph()):
        r = analyze(from_nx(G).to_dict())["planarity"]
        assert r["planar"] and not r["virtual_nodes"]
        assert count_crossings(r["positions"], [(s["source"], s["target"]) for s in r["segments"]]) == 0


if __name__ == "__main__":
    for t in (test_structure, test_coloring, test_planarity):
        t()
        print("OK", t.__name__)
