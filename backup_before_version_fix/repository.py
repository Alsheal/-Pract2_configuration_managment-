
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


def _fetch_json(url: str) -> dict[str, Any]:
    """Получает JSON по HTTP."""
    request = Request(
        url,
        headers={"User-Agent": "dependency-visualizer/1.0"},
    )

    try:
        with urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise RepositoryError(
                f"Пакет или версия не найдены: {url}"
            ) from exc
        raise RepositoryError(
            f"Ошибка HTTP {exc.code} при обращении к Cargo-репозиторию."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RepositoryError(
            f"Не удалось подключиться к Cargo-репозиторию: {exc}"
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepositoryError(
            f"Сервер вернул некорректный JSON: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise RepositoryError("Некорректный ответ Cargo-репозитория.")

    return data


def _cargo_api_url(repository_url: str, package_name: str) -> str:
    """Формирует адрес API crates.io для указанного пакета."""
    base_url = repository_url.rstrip("/")

    if base_url.endswith("/api/v1"):
        api_url = base_url
    else:
        api_url = f"{base_url}/api/v1"

    return f"{api_url}/crates/{quote(package_name, safe='')}"



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
            return (
                actual >= requested
                and actual[0] == requested[0]
            )
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


def load_cargo_repository(
    repository_url: str,
    package_name: str,
    version: str,
    max_depth: int = 2,
) -> dict[str, dict[str, Any]]:
    """Загружает зависимости Cargo из Sparse Index до заданной глубины.

    Для каждой зависимости выбирается последняя доступная версия,
    удовлетворяющая распространённым ограничениям Cargo.
    """
    if not isinstance(max_depth, int) or isinstance(max_depth, bool):
        raise RepositoryError("max_depth должен быть целым числом.")
    if max_depth < 0:
        raise RepositoryError("max_depth не может быть отрицательным.")

    if "index.crates.io" not in repository_url and "crates.io" not in repository_url:
        raise RepositoryError(
            "Для удалённого режима укажите репозиторий crates.io."
        )

    packages: dict[str, dict[str, Any]] = {}
    pending = [(package_name, version, 0)]

    while pending:
        current_name, required_version, depth = pending.pop()

        if current_name in packages:
            continue

        records = _fetch_cargo_index(current_name)

        available = [
            record
            for record in records
            if not record.get("yanked", False)
            and _version_matches(record["vers"], required_version)
        ]

        if not available:
            raise RepositoryError(
                f"Не найдена подходящая версия пакета "
                f"'{current_name}' для ограничения '{required_version}'."
            )

        selected = max(
            available,
            key=lambda record: _version_tuple(record["vers"]),
        )

        dependencies = []
        dependency_names = set()

        for dependency in selected.get("deps", []):
            if dependency.get("kind") not in (None, "normal", "build"):
                continue
            if dependency.get("optional", False):
                continue

            dependency_name = dependency.get("name")
            dependency_requirement = dependency.get("req", "*")

            if not isinstance(dependency_name, str):
                continue
            if dependency_name in dependency_names:
                continue

            dependency_names.add(dependency_name)
            dependencies.append(dependency_name)

            if depth < max_depth and dependency_name not in packages:
                pending.append((
                    dependency_name,
                    dependency_requirement,
                    depth + 1,
                ))

        packages[current_name] = {
            "version": selected["vers"],
            "dependencies": dependencies,
        }

    return packages
