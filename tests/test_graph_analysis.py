import math

from graph_analysis import (
    extract_links,
    calculate_statistics,
    pagerank,
    best_closeness_node,
)


def test_extract_links():

    html = """
    <a HREF="17.html">Link</a>
    <a HREF="42.html">Link</a>
    <a HREF="17.html">Link</a>
    """

    assert extract_links(html) == [17, 42, 17]


def test_statistics():

    values = [1, 2, 3, 4, 5]

    stats = calculate_statistics(values)

    assert stats["average"] == 3
    assert stats["median"] == 3
    assert stats["minimum"] == 1
    assert stats["maximum"] == 5


def test_pagerank_known_graph():
    """
    Graph:

        A -> B
        A -> C
        B -> C
        C -> A

    Analytical PageRank with d=0.85:

        A = 686 / 1769
        B = 380 / 1769
        C = 703 / 1769
    """

    adjacency = [
        [1, 2],
        [2],
        [0],
    ]

    ranks, iterations = pagerank(
        adjacency,
        damping=0.85,
        tolerance=1e-12
    )

    expected = [
        686 / 1769,
        380 / 1769,
        703 / 1769,
    ]

    for actual, correct in zip(ranks, expected):
        assert math.isclose(
            actual,
            correct,
            rel_tol=1e-8,
            abs_tol=1e-8
        )

    assert math.isclose(
        sum(ranks),
        1.0,
        rel_tol=1e-10
    )


def test_closeness_centrality():
    """
           0
           |
       2 - 1 - 3

    All edges are bidirectional.

    Distances from node 1:
        d(1,0) = 1
        d(1,2) = 1
        d(1,3) = 1

    Therefore:
        closeness(1) = 3 / 3 = 1

    Node 1 must have the best closeness.
    """

    adjacency = [
        [1],
        [0, 2, 3],
        [1],
        [1],
    ]

    node, score = best_closeness_node(adjacency)

    assert node == 1

    assert math.isclose(
        score,
        1.0,
        rel_tol=1e-12
    )
