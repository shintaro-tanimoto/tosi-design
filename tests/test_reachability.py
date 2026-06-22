import networkx as nx

from nmincity.core.reachability import reachable_categories, reachable_nodes


def _line_graph():
    graph = nx.MultiDiGraph()
    graph.add_edge("O", "A", travel_time=60)
    graph.add_edge("A", "B", travel_time=120)
    graph.add_edge("B", "C", travel_time=180)
    return graph


def test_reachable_nodes_respects_cutoff_including_boundary():
    graph = _line_graph()

    assert reachable_nodes(graph, "O", 0) == {"O"}
    assert reachable_nodes(graph, "O", 60) == {"O", "A"}
    assert reachable_nodes(graph, "O", 180) == {"O", "A", "B"}


def test_reachable_categories_uses_single_reachability_result():
    graph = _line_graph()
    category_nodes = {"goods": {"B"}, "health": {"C"}}

    result = reachable_categories(graph, "O", 180, category_nodes)

    assert result["goods"] is True
    assert result["health"] is False


def test_reachable_nodes_includes_origin():
    graph = _line_graph()

    assert "O" in reachable_nodes(graph, "O", 1)
