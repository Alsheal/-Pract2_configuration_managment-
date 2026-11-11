
"""Построение и анализ графа зависимостей."""

from typing import Any

from dependency_visualizer.analyzer import (
    DependencyAnalysisError,
    analyze_dependencies,
)


class DependencyGraphError(ValueError):
    """Ошибка построения графа зависимостей."""


def _create_nodes(
    packages: dict[str, dict[str, Any]],
    package_name: str,
    dependencies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Создаёт вершины графа."""
    root_package = packages[package_name]

    root_node = {
        "id": package_name,
        "name": root_package.get("name", package_name),
        "version": root_package["version"],
        "depth": 0,
    }

    return [root_node, *dependencies]


def _create_edges(
    packages: dict[str, dict[str, Any]],
    nodes: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Создаёт уникальные рёбра между найденными вершинами."""
    node_ids = {node["id"] for node in nodes}
    edges = []
    seen_edges = set()

    for node in nodes:
        source = node["id"]

        for target in packages[source]["dependencies"]:
            edge = (source, target)

            if target not in node_ids or edge in seen_edges:
                continue

            seen_edges.add(edge)
            edges.append({
                "source": source,
                "target": target,
            })

    return edges


def build_dependency_graph(
    packages: dict[str, dict[str, Any]],
    package_name: str,
    max_depth: int,
) -> dict[str, Any]:
    """Строит направленный граф зависимостей выбранного пакета."""
    try:
        dependencies = analyze_dependencies(
            packages,
            package_name,
            max_depth,
        )
    except DependencyAnalysisError as exc:
        raise DependencyGraphError(str(exc)) from exc

    nodes = _create_nodes(packages, package_name, dependencies)
    edges = _create_edges(packages, nodes)

    return {
        "root": package_name,
        "nodes": nodes,
        "edges": edges,
    }


def _build_adjacency(
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, str]],
) -> dict[str, list[str]]:
    """Создаёт список смежности графа."""
    adjacency = {package_id: [] for package_id in nodes}

    for edge in edges:
        adjacency[edge["source"]].append(edge["target"])

    return adjacency


def _traverse_graph(
    root: str,
    adjacency: dict[str, list[str]],
) -> tuple[list[str], list[tuple[str, str]]]:
    """Выполняет итеративный DFS и находит циклические рёбра."""
    state = {package_id: 0 for package_id in adjacency}
    state[root] = 1

    stack = [[root, 0]]
    order = []
    cycles = []

    while stack:
        package_id, index = stack[-1]
        dependencies = adjacency[package_id]

        if index >= len(dependencies):
            stack.pop()
            state[package_id] = 2
            order.append(package_id)
            continue

        dependency = dependencies[index]
        stack[-1][1] += 1

        if state[dependency] == 0:
            state[dependency] = 1
            stack.append([dependency, 0])
        elif state[dependency] == 1:
            cycle = (package_id, dependency)

            if cycle not in cycles:
                cycles.append(cycle)

    return order, cycles


def get_dependency_load_order(
    graph: dict[str, Any],
) -> dict[str, Any]:
    """Определяет порядок загрузки с помощью итеративного DFS."""
    nodes = {node["id"]: node for node in graph["nodes"]}
    adjacency = _build_adjacency(nodes, graph["edges"])

    order, cycles = _traverse_graph(graph["root"], adjacency)

    return {
        "order": [
            nodes[package_id]["name"] + "@" + nodes[package_id]["version"]
            for package_id in order
        ],
        "order_ids": order,
        "cycles": cycles,
    }
