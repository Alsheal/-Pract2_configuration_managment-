"""Загрузка тестового и удалённого Cargo-репозитория."""

import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import yaml


class RepositoryError(ValueError):
    """Ошибка формата или содержимого репозитория."""


def load_repository(path: str | Path) -> dict[str, dict[str, Any]]:
    """Загружает пакеты из YAML-файла тестового репозитория."""
    repository_path = Path(path)

    if not repository_path.is_file():
        raise RepositoryError(
            f"Файл репозитория не найден: {repository_path}"
        )

    try:
        with repository_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise RepositoryError(f"Некорректный YAML: {exc}") from exc
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
            raise RepositoryError(
                "Имя пакета должно быть непустой строкой."
            )

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


def _cargo_index_path(package_name: str) -> str:
    """Формирует путь пакета в Sparse Index Cargo."""
    name = package_name.lower()

    if len(name) == 1:
        return f"1/{name}"
    if len(name) == 2:
        return f"2/{name}"
    if len(name) == 3:
        return f"3/{name[0]}/{name}"

    return f"{name[:2]}/{name[2:4]}/{name}"


def _fetch_cargo_index(package_name: str) -> list[dict[str, Any]]:
    """Загружает записи о версиях пакета из Sparse Index."""
    url = (
        "https://index.crates.io/"
        + _cargo_index_path(package_name)
    )

    request = Request(
        url,
        headers={"User-Agent": "dependency-visualizer/1.0"},
    )

    try:
        with urlopen(request, timeout=20) as response:
            content = response.read().decode("utf-8")
    except HTTPError as exc:
        raise RepositoryError(
            f"Ошибка HTTP {exc.code} при загрузке пакета "
            f"'{package_name}' из Cargo Index."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RepositoryError(
            f"Не удалось загрузить пакет '{package_name}': {exc}"
        ) from exc

    records = []

    try:
        for line in content.splitlines():
            if line.strip():
                records.append(json.loads(line))
    except json.JSONDecodeError as exc:
        raise RepositoryError(
            f"Некорректные данные Cargo Index для '{package_name}'."
        ) from exc

    if not records:
        raise RepositoryError(
            f"Пакет '{package_name}' не найден в Cargo Index."
        )

    return records


def _version_tuple(version: str) -> tuple[int, int, int]:
    """Преобразует номер версии в числовой кортеж."""
    parts = version.split("-")[0].split(".")

    try:
        numbers = [int(part) for part in parts[:3]]
    except ValueError as exc:
        raise RepositoryError(
            f"Неподдерживаемый формат версии: {version}"
        ) from exc

    while len(numbers) < 3:
        numbers.append(0)

    return tuple(numbers)


def _version_matches(version: str, requirement: str) -> bool:
    """Проверяет распространённые ограничения версий Cargo."""
    actual = _version_tuple(version)
    requirement = requirement.strip()

    if requirement in ("", "*"):
        return True

    if requirement.startswith("^"):
        requested = _version_tuple(requirement[1:])

        if requested[0] > 0:
            return actual >= requested and actual[0] == requested[0]

        if requested[1] > 0:
            return (
                actual >= requested
                and actual[0] == 0
                and actual[1] == requested[1]
            )

        return actual == requested

    if requirement.startswith("~"):
        requested = _version_tuple(requirement[1:])
        return (
            actual >= requested
            and actual[0] == requested[0]
            and actual[1] == requested[1]
        )

    if requirement.startswith(">="):
        return actual >= _version_tuple(requirement[2:])

    if requirement.startswith("<="):
        return actual <= _version_tuple(requirement[2:])

    if requirement.startswith(">"):
        return actual > _version_tuple(requirement[1:])

    if requirement.startswith("<"):
        return actual < _version_tuple(requirement[1:])

    if requirement.startswith("="):
        return actual == _version_tuple(requirement[1:])

    if "*" in requirement or "x" in requirement.lower():
        parts = requirement.lower().replace("x", "*").split(".")

        for index, part in enumerate(parts):
            if part == "*":
                return True

            if index >= len(actual) or int(part) != actual[index]:
                return False

        return True

    return actual == _version_tuple(requirement)


def _select_version(
    package_name: str,
    requirement: str,
) -> dict[str, Any]:
    """Выбирает последнюю подходящую версию пакета."""
    records = _fetch_cargo_index(package_name)

    available = [
        record
        for record in records
        if not record.get("yanked", False)
        and _version_matches(record["vers"], requirement)
    ]

    if not available:
        raise RepositoryError(
            f"Не найдена подходящая версия пакета "
            f"'{package_name}' для ограничения '{requirement}'."
        )

    return max(
        available,
        key=lambda record: _version_tuple(record["vers"]),
    )


def load_cargo_repository(
    repository_url: str,
    package_name: str,
    version: str,
    max_depth: int = 2,
) -> dict[str, dict[str, Any]]:
    """Загружает версии пакетов Cargo до заданной глубины.

    Идентификатор каждой вершины включает имя и версию.
    Поэтому разные версии одной библиотеки не объединяются.
    """
    if not isinstance(max_depth, int) or isinstance(max_depth, bool):
        raise RepositoryError("max_depth должен быть целым числом.")

    if max_depth < 0:
        raise RepositoryError("max_depth не может быть отрицательным.")

    if (
        "index.crates.io" not in repository_url
        and "crates.io" not in repository_url
    ):
        raise RepositoryError(
            "Для удалённого режима укажите репозиторий crates.io."
        )

    root_record = _select_version(package_name, f"={version}")
    root_id = f"{package_name}@{root_record['vers']}"

    packages: dict[str, dict[str, Any]] = {}
    pending = [(package_name, f"={version}", 0)]
    processed = set()

    while pending:
        current_name, required_version, depth = pending.pop()

        selected = _select_version(current_name, required_version)
        selected_version = selected["vers"]
        package_id = f"{current_name}@{selected_version}"

        if package_id in processed:
            continue

        processed.add(package_id)

        dependencies = []
        dependency_ids = set()

        for dependency in selected.get("deps", []):
            if dependency.get("kind") not in (None, "normal", "build"):
                continue

            if dependency.get("optional", False):
                continue

            if dependency.get("target") is not None:
                continue

            dependency_name = dependency.get("name")
            dependency_requirement = dependency.get("req", "*")

            if not isinstance(dependency_name, str):
                continue

            if depth < max_depth:
                dependency_record = _select_version(
                    dependency_name,
                    dependency_requirement,
                )
                dependency_id = (
                    f"{dependency_name}@{dependency_record['vers']}"
                )
            else:
                continue

            if dependency_id not in dependency_ids:
                dependency_ids.add(dependency_id)
                dependencies.append(dependency_id)

            if dependency_id not in processed:
                pending.append((
                    dependency_name,
                    f"={dependency_record['vers']}",
                    depth + 1,
                ))

        packages[package_id] = {
            "name": current_name,
            "version": selected_version,
            "dependencies": dependencies,
        }

    if root_id not in packages:
        raise RepositoryError(
            f"Не удалось загрузить корневой пакет '{root_id}'."
        )

    return packages
