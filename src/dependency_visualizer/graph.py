from typing import Any

from dependency_visualizer.analyzer import (
    DependencyAnalysisError,
    analyze_dependencies,
)


class DependencyGraphError(ValueError):
    """Ошибка построения графа зависимостей."""


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

    root_package = packages[package_name]

    nodes = [
        {
            "id": package_name,
            "name": root_package.get("name", package_name),
            "version": root_package["version"],
            "depth": 0,
        }
    ]

    nodes.extend(dependencies)

    node_ids = {node["id"] for node in nodes}
    edges = []
    seen_edges = set()

    for node in nodes:
        source = node["id"]

        for target in packages[source]["dependencies"]:
            if target not in node_ids:
                continue

            edge = (source, target)

            if edge in seen_edges:
                continue

            seen_edges.add(edge)
            edges.append({
                "source": source,
                "target": target,
            })

    return {
        "root": package_name,
        "nodes": nodes,
        "edges": edges,
    }


def get_dependency_load_order(
    graph: dict[str, Any],
) -> dict[str, Any]:
    """Определяет порядок загрузки с помощью итеративного DFS."""
    nodes = {node["id"]: node for node in graph["nodes"]}

    adjacency: dict[str, list[str]] = {
        package_id: [] for package_id in nodes
    }

    for edge in graph["edges"]:
        adjacency[edge["source"]].append(edge["target"])

    root = graph["root"]
    state = {package_id: 0 for package_id in nodes}
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

    return {
        "order": [
            nodes[package_id]["name"] + "@" + nodes[package_id]["version"]
            for package_id in order
        ],
        "order_ids": order,
        "cycles": cycles,
    }
