from collections import deque
from typing import Any


class DependencyAnalysisError(ValueError):
    """Ошибка анализа зависимостей."""


def analyze_dependencies(
    packages: dict[str, dict[str, Any]],
    package_name: str,
    max_depth: int,
) -> list[dict[str, Any]]:
    """Возвращает зависимости пакета с указанием глубины."""
    if package_name not in packages:
        raise DependencyAnalysisError(
            f"Пакет '{package_name}' не найден в репозитории."
        )

    if not isinstance(max_depth, int) or isinstance(max_depth, bool):
        raise DependencyAnalysisError(
            "max_depth должен быть целым числом."
        )

    if max_depth < 0:
        raise DependencyAnalysisError(
            "max_depth не может быть отрицательным."
        )
    if max_depth == 0:
        return []

    result = []
    visited = {package_name}
    queue = deque()

    for dependency in packages[package_name]["dependencies"]:
        queue.append((dependency, 1))

    while queue:
        name, depth = queue.popleft()

        if name in visited:
            continue

        visited.add(name)
        package = packages[name]

        result.append({
            "name": name,
            "version": package["version"],
            "depth": depth,
        })

        if depth < max_depth:
            for dependency in package["dependencies"]:
                if dependency not in visited:
                    queue.append((dependency, depth + 1))

    return result
