from pathlib import Path
from typing import Any

import yaml


class RepositoryError(ValueError):
    """Ошибка формата или содержимого репозитория."""


def load_repository(path: str | Path) -> dict[str, dict[str, Any]]:
    """Загружает пакеты из YAML-файла репозитория."""
    repository_path = Path(path)

    if not repository_path.is_file():
        raise RepositoryError(
            f"Файл репозитория не найден: {repository_path}"
        )

    try:
        with repository_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise RepositoryError(
            f"Некорректный YAML: {exc}"
        ) from exc
    except OSError as exc:
        raise RepositoryError(
            f"Не удалось прочитать репозиторий: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise RepositoryError(
            "Корень репозитория должен быть словарём."
        )

    packages = data.get("packages")

    if not isinstance(packages, dict) or not packages:
        raise RepositoryError(
            "Репозиторий должен содержать непустой словарь packages."
        )

    for name, package in packages.items():
        if not isinstance(name, str) or not name.strip():
            raise RepositoryError("Имя пакета должно быть непустой строкой.")

        if not isinstance(package, dict):
            raise RepositoryError(
                f"Описание пакета '{name}' должно быть словарём."
            )

        version = package.get("version")
        dependencies = package.get("dependencies")

        if not isinstance(version, str) or not version.strip():
            raise RepositoryError(
                f"У пакета '{name}' отсутствует корректная version."
            )

        if not isinstance(dependencies, list):
            raise RepositoryError(
                f"Зависимости пакета '{name}' должны быть списком."
            )

        for dependency in dependencies:
            if not isinstance(dependency, str) or not dependency.strip():
                raise RepositoryError(
                    f"Некорректная зависимость пакета '{name}'."
                )

    for name, package in packages.items():
        for dependency in package["dependencies"]:
            if dependency not in packages:
                raise RepositoryError(
                    f"Пакет '{name}' зависит от отсутствующего "
                    f"пакета '{dependency}'."
                )

    return packages
