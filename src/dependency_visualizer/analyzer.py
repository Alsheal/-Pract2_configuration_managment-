"""Анализ графа зависимостей пакетов."""

from typing import Any


class DependencyAnalysisError(ValueError):
    """Ошибка анализа зависимостей."""


def _validate_input(
    packages: dict[str, dict[str, Any]],
    package_name: str,
    max_depth: int,
) -> None:
    """Проверяет исходный пакет и глубину анализа."""
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


def _initial_stack(
    packages: dict[str, dict[str, Any]],
    package_name: str,
) -> list[tuple[str, int]]:
    """Формирует начальный стек обхода DFS."""
    return [
        (dependency, 1)
        for dependency in reversed(
            packages[package_name]["dependencies"]
        )
    ]


def _make_entry(
    package_id: str,
    package: dict[str, Any],
    depth: int,
) -> dict[str, Any]:
    """Формирует запись о найденной зависимости."""
    return {
        "id": package_id,
        "name": package.get("name", package_id),
        "version": package["version"],
        "depth": depth,
    }


def _push_children(
    stack: list[tuple[str, int]],
    package: dict[str, Any],
    depth: int,
    max_depth: int,
    visited: set[str],
) -> None:
    """Добавляет в стек непосещённые зависимости пакета."""
    if depth >= max_depth:
        return

    for dependency in reversed(package["dependencies"]):
        if dependency not in visited:
            stack.append((dependency, depth + 1))


def analyze_dependencies(
    packages: dict[str, dict[str, Any]],
    package_name: str,
    max_depth: int,
) -> list[dict[str, Any]]:
    """Находит транзитивные зависимости итеративным обходом DFS."""
    _validate_input(packages, package_name, max_depth)

    if max_depth == 0:
        return []

    result: list[dict[str, Any]] = []
    visited = {package_name}
    stack = _initial_stack(packages, package_name)

    while stack:
        package_id, depth = stack.pop()

        if package_id in visited:
            continue

        if package_id not in packages:
            raise DependencyAnalysisError(
                f"Зависимость '{package_id}' не найдена."
            )

        visited.add(package_id)
        package = packages[package_id]
        result.append(_make_entry(package_id, package, depth))
        _push_children(stack, package, depth, max_depth, visited)

    return result
