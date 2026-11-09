
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
    """Строит направленный граф зависимостей выбранного пакета.

    Вершины графа содержат имя пакета, версию и глубину.
    Рёбра направлены от пакета к его зависимости.
    """
    try:
        dependencies = analyze_dependencies(
            packages,
            package_name,
            max_depth,
        )
    except DependencyAnalysisError as exc:
        raise DependencyGraphError(str(exc)) from exc

    nodes = [
        {
            "name": package_name,
            "version": packages[package_name]["version"],
            "depth": 0,
        }
    ]

    nodes.extend(dependencies)

    node_names = {node["name"] for node in nodes}
    edges = []
    seen_edges = set()

    for node in nodes:
        source = node["name"]

        for target in packages[source]["dependencies"]:
            if target not in node_names:
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
    """Возвращает порядок загрузки пакетов с помощью итеративного DFS.

    Зависимости помещаются в результат раньше пакетов, которые от них
    зависят. Циклические рёбра фиксируются отдельно.
    """
    nodes = {node["name"] for node in graph["nodes"]}
    adjacency: dict[str, list[str]] = {
        name: [] for name in nodes
    }

    for edge in graph["edges"]:
        adjacency[edge["source"]].append(edge["target"])

    root = graph["root"]
    state = {name: 0 for name in nodes}
    state[root] = 1

    # В стеке хранятся пакет и индекс следующей зависимости.
    stack = [[root, 0]]
    order = []
    cycles = []

    while stack:
        name, index = stack[-1]
        dependencies = adjacency[name]

        if index >= len(dependencies):
            stack.pop()
            state[name] = 2
            order.append(name)
            continue

        dependency = dependencies[index]
        stack[-1][1] += 1

        if state[dependency] == 0:
            state[dependency] = 1
            stack.append([dependency, 0])
        elif state[dependency] == 1:
            cycle = (name, dependency)
            if cycle not in cycles:
                cycles.append(cycle)

    return {
        "order": order,
        "cycles": cycles,
    }
