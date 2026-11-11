
"""Анализ графа зависимостей пакетов."""

from typing import Any


class DependencyAnalysisError(ValueError):
    """Ошибка анализа зависимостей."""


def _validate_input(
    packages: dict[str, dict[str, Any]],
    package_name: str,
    max_depth: int,
) -> None:
    """Проверяет исходный пакет и максимальную глубину."""
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


def _create_stack(
    dependencies: list[str],
) -> list[tuple[str, int]]:
    """Создаёт начальный стек для итеративного DFS."""
    return [(dependency, 1) for dependency in reversed(dependencies)]


def _process_dependency(
    package_id: str,
    depth: int,
    packages: dict[str, dict[str, Any]],
    visited: set[str],
    result: list[dict[str, Any]],
    stack: list[tuple[str, int]],
    max_depth: int,
) -> None:
    """Обрабатывает пакет и добавляет его зависимости в стек."""
    if package_id in visited:
        return

    if package_id not in packages:
        raise DependencyAnalysisError(
            f"Зависимость '{package_id}' не найдена в репозитории."
        )

    visited.add(package_id)
    package = packages[package_id]

    result.append({
        "id": package_id,
        "name": package.get("name", package_id),
        "version": package["version"],
        "depth": depth,
    })

    if depth < max_depth:
        for dependency in reversed(package["dependencies"]):
            if dependency not in visited:
                stack.append((dependency, depth + 1))


def analyze_dependencies(
    packages: dict[str, dict[str, Any]],
    package_name: str,
    max_depth: int,
) -> list[dict[str, Any]]:
    """Выполняет итеративный DFS и возвращает найденные зависимости."""
    _validate_input(packages, package_name, max_depth)

    if max_depth == 0:
        return []

    result = []
    visited = {package_name}
    stack = _create_stack(packages[package_name]["dependencies"])

    while stack:
        package_id, depth = stack.pop()
        _process_dependency(
            package_id,
            depth,
            packages,
            visited,
            result,
            stack,
            max_depth,
        )

    return result
