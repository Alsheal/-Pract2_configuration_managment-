
from typing import Any


class DependencyAnalysisError(ValueError):
    """Ошибка анализа зависимостей."""


def analyze_dependencies(
    packages: dict[str, dict[str, Any]],
    package_name: str,
    max_depth: int,
) -> list[dict[str, Any]]:
    """Возвращает зависимости пакета с указанием глубины.

    Используется итеративный обход в глубину (DFS) без рекурсии.
    """
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

    # Стек содержит имя пакета и глубину его расположения.
    stack = []

    # Обратный порядок нужен для сохранения порядка зависимостей
    # при использовании стека.
    for dependency in reversed(packages[package_name]["dependencies"]):
        stack.append((dependency, 1))

    while stack:
        name, depth = stack.pop()

        if name in visited:
            continue

        visited.add(name)

        if name not in packages:
            raise DependencyAnalysisError(
                f"Зависимость '{name}' не найдена в репозитории."
            )

        package = packages[name]

        result.append({
            "name": name,
            "version": package["version"],
            "depth": depth,
        })

        if depth < max_depth:
            for dependency in reversed(package["dependencies"]):
                if dependency not in visited:
                    stack.append((dependency, depth + 1))

    return result
