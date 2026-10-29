
import pytest

from dependency_visualizer.graph import (
    DependencyGraphError,
    build_dependency_graph,
)


@pytest.fixture
def packages():
    return {
        "serde": {
            "version": "1.0.0",
            "dependencies": ["syn", "quote"],
        },
        "syn": {
            "version": "2.0.0",
            "dependencies": ["unicode-ident"],
        },
        "quote": {
            "version": "1.0.0",
            "dependencies": [],
        },
        "unicode-ident": {
            "version": "1.0.0",
            "dependencies": [],
        },
    }


def test_build_graph_contains_root_and_dependencies(packages):
    graph = build_dependency_graph(packages, "serde", 3)

    assert graph["root"] == "serde"
    assert {node["name"] for node in graph["nodes"]} == {
        "serde",
        "syn",
        "quote",
        "unicode-ident",
    }


def test_root_has_depth_zero(packages):
    graph = build_dependency_graph(packages, "serde", 3)

    root = next(
        node for node in graph["nodes"]
        if node["name"] == "serde"
    )

    assert root["depth"] == 0


def test_graph_contains_directed_edges(packages):
    graph = build_dependency_graph(packages, "serde", 3)

    assert {"source": "serde", "target": "syn"} in graph["edges"]
    assert {"source": "serde", "target": "quote"} in graph["edges"]
    assert {
        "source": "syn",
        "target": "unicode-ident",
    } in graph["edges"]


def test_max_depth_limits_graph(packages):
    graph = build_dependency_graph(packages, "serde", 1)

    names = {node["name"] for node in graph["nodes"]}

    assert names == {"serde", "syn", "quote"}
    assert all(
        node["depth"] <= 1
        for node in graph["nodes"]
    )


def test_zero_depth_contains_only_root(packages):
    graph = build_dependency_graph(packages, "serde", 0)

    assert [node["name"] for node in graph["nodes"]] == ["serde"]
    assert graph["edges"] == []


def test_graph_does_not_duplicate_nodes_or_edges():
    packages_with_duplicates = {
        "app": {
            "version": "1.0.0",
            "dependencies": ["lib", "lib"],
        },
        "lib": {
            "version": "1.0.0",
            "dependencies": [],
        },
    }

    graph = build_dependency_graph(
        packages_with_duplicates,
        "app",
        2,
    )

    node_names = [node["name"] for node in graph["nodes"]]

    assert len(node_names) == len(set(node_names))
    assert graph["edges"] == [
        {"source": "app", "target": "lib"}
    ]


def test_graph_handles_cycles():
    packages_with_cycle = {
        "app": {
            "version": "1.0.0",
            "dependencies": ["lib"],
        },
        "lib": {
            "version": "1.0.0",
            "dependencies": ["app"],
        },
    }

    graph = build_dependency_graph(
        packages_with_cycle,
        "app",
        3,
    )

    assert {node["name"] for node in graph["nodes"]} == {
        "app",
        "lib",
    }
    assert {"source": "app", "target": "lib"} in graph["edges"]
    assert {"source": "lib", "target": "app"} in graph["edges"]


def test_missing_package_raises_error(packages):
    with pytest.raises(DependencyGraphError, match="не найден"):
        build_dependency_graph(packages, "missing", 2)


@pytest.mark.parametrize("max_depth", [-1, 1.5, True])
def test_invalid_max_depth_raises_error(packages, max_depth):
    with pytest.raises(DependencyGraphError):
        build_dependency_graph(packages, "serde", max_depth)
