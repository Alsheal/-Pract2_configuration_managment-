
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
