"""Загрузка тестового и удалённого Cargo-репозитория."""

import json
import operator
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

CARGO_INDEX_URL = "https://index.crates.io/"
CARGO_USER_AGENT = "dependency-visualizer/1.0"
REQUEST_TIMEOUT = 20

SINGLE_CHARACTER_NAME_LENGTH = 1
TWO_CHARACTER_NAME_LENGTH = 2
THREE_CHARACTER_NAME_LENGTH = 3
VERSION_PARTS_COUNT = 3

INDEX_SHORT_NAME_PREFIX = "1"
INDEX_TWO_NAME_PREFIX = "2"
INDEX_THREE_NAME_PREFIX = "3"
INDEX_FIRST_SLICE_END = 2
INDEX_SECOND_SLICE_START = 2
INDEX_SECOND_SLICE_END = 4

CARET_PREFIX = "^"
TILDE_PREFIX = "~"
WILDCARD_CHARS = ("*", "x")
EMPTY_REQUIREMENT = ("", "*")

MAJOR_INDEX = 0
MINOR_INDEX = 1

OPERATORS: tuple[tuple[str, Callable], ...] = (
    (">=", operator.ge),
    ("<=", operator.le),
    (">", operator.gt),
    ("<", operator.lt),
    ("=", operator.eq),
)

SUPPORTED_DEPENDENCY_KINDS = (None, "normal", "build")


class RepositoryError(ValueError):
    """Ошибка формата или содержимого репозитория."""


def _read_repository_file(path: str | Path) -> Any:
    """Читает YAML-файл репозитория."""
    repository_path = Path(path)

    if not repository_path.is_file():
        raise RepositoryError(
            f"Файл репозитория не найден: {repository_path}"
        )

    try:
        with repository_path.open("r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise RepositoryError(
            f"Некорректный YAML: {exc}"
        ) from exc
    except OSError as exc:
        raise RepositoryError(
            f"Не удалось прочитать репозиторий: {exc}"
        ) from exc


def _extract_packages(data: Any) -> dict[str, dict[str, Any]]:
    """Проверяет корневую структуру и извлекает пакеты."""
    if not isinstance(data, dict):
        raise RepositoryError(
            "Корень репозитория должен быть словарём."
        )

    packages = data.get("packages")

    if not isinstance(packages, dict) or not packages:
        raise RepositoryError(
            "Репозиторий должен содержать непустой словарь packages."
        )

    return packages


def _validate_package(name: str, package: Any) -> None:
    """Проверяет описание одного пакета."""
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


def _validate_dependency_references(
    packages: dict[str, dict[str, Any]],
) -> None:
    """Проверяет наличие всех указанных зависимостей."""
    for name, package in packages.items():
        for dependency in package["dependencies"]:
            if dependency not in packages:
                raise RepositoryError(
                    f"Пакет '{name}' зависит от отсутствующего "
                    f"пакета '{dependency}'."
                )


def load_repository(path: str | Path) -> dict[str, dict[str, Any]]:
    """Загружает и проверяет YAML-репозиторий."""
    data = _read_repository_file(path)
    packages = _extract_packages(data)

    for name, package in packages.items():
        _validate_package(name, package)

    _validate_dependency_references(packages)

    return packages


def _cargo_index_path(package_name: str) -> str:
    """Формирует путь пакета в Sparse Index Cargo."""
    name = package_name.lower()
    length = len(name)

    if length == SINGLE_CHARACTER_NAME_LENGTH:
        return f"{INDEX_SHORT_NAME_PREFIX}/{name}"

    if length == TWO_CHARACTER_NAME_LENGTH:
        return f"{INDEX_TWO_NAME_PREFIX}/{name}"

    if length == THREE_CHARACTER_NAME_LENGTH:
        return f"{INDEX_THREE_NAME_PREFIX}/{name[0]}/{name}"

    first = name[:INDEX_FIRST_SLICE_END]
    second = name[INDEX_SECOND_SLICE_START:INDEX_SECOND_SLICE_END]
    return f"{first}/{second}/{name}"


def _parse_cargo_index(
    content: str,
    package_name: str,
) -> list[dict[str, Any]]:
    """Преобразует строки Cargo Index в список записей."""
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


def _fetch_cargo_index(package_name: str) -> list[dict[str, Any]]:
    """Загружает записи о версиях пакета из Sparse Index."""
    url = CARGO_INDEX_URL + _cargo_index_path(package_name)

    request = Request(
        url,
        headers={"User-Agent": CARGO_USER_AGENT},
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
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

    return _parse_cargo_index(content, package_name)


def _version_tuple(version: str) -> tuple[int, int, int]:
    """Преобразует номер версии в числовой кортеж."""
    parts = version.split("-")[0].split(".")

    try:
        numbers = [
            int(part)
            for part in parts[:VERSION_PARTS_COUNT]
        ]
    except ValueError as exc:
        raise RepositoryError(
            f"Неподдерживаемый формат версии: {version}"
        ) from exc

    while len(numbers) < VERSION_PARTS_COUNT:
        numbers.append(0)

    return tuple(numbers)


def _matches_caret(
    actual: tuple[int, int, int],
    requirement: str,
) -> bool:
    """Проверяет ограничение совместимости ^."""
    requested = _version_tuple(requirement[len(CARET_PREFIX):])

    if requested[MAJOR_INDEX] > 0:
        return (
            actual >= requested
            and actual[MAJOR_INDEX] == requested[MAJOR_INDEX]
        )

    if requested[MINOR_INDEX] > 0:
        return (
            actual >= requested
            and actual[MAJOR_INDEX] == 0
            and actual[MINOR_INDEX] == requested[MINOR_INDEX]
        )

    return actual == requested


def _matches_tilde(
    actual: tuple[int, int, int],
    requirement: str,
) -> bool:
    """Проверяет ограничение совместимости ~."""
    requested = _version_tuple(requirement[len(TILDE_PREFIX):])

    return (
        actual >= requested
        and actual[MAJOR_INDEX] == requested[MAJOR_INDEX]
        and actual[MINOR_INDEX] == requested[MINOR_INDEX]
    )


def _matches_wildcard(
    actual: tuple[int, int, int],
    requirement: str,
) -> bool:
    """Проверяет ограничение версии с подстановочными знаками."""
    parts = requirement.lower().replace("x", "*").split(".")

    for index, part in enumerate(parts):
        if part == "*":
            return True

        if index >= len(actual) or int(part) != actual[index]:
            return False

    return True


def _match_operator(
    actual: tuple[int, int, int],
    requirement: str,
) -> bool | None:
    """Применяет оператор сравнения версий.

    Возвращает True/False при распознанном префиксе,
    либо None, если префикс не является оператором.
    """
    for prefix, comparator in OPERATORS:
        if requirement.startswith(prefix):
            requested = _version_tuple(requirement[len(prefix):])
            return comparator(actual, requested)
    return None


def _version_matches(version: str, requirement: str) -> bool:
    """Проверяет распространённые ограничения версий Cargo."""
    actual = _version_tuple(version)
    requirement = requirement.strip()

    if requirement in EMPTY_REQUIREMENT:
        return True

    if requirement.startswith(CARET_PREFIX):
        return _matches_caret(actual, requirement)

    if requirement.startswith(TILDE_PREFIX):
        return _matches_tilde(actual, requirement)

    result = _match_operator(actual, requirement)
    if result is not None:
        return result

    if any(ch in requirement.lower() for ch in WILDCARD_CHARS):
        return _matches_wildcard(actual, requirement)

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


def _validate_cargo_arguments(
    repository_url: str,
    max_depth: int,
) -> None:
    """Проверяет URL репозитория и максимальную глубину."""
    if not isinstance(max_depth, int) or isinstance(max_depth, bool):
        raise RepositoryError(
            "max_depth должен быть целым числом."
        )

    if max_depth < 0:
        raise RepositoryError(
            "max_depth не может быть отрицательным."
        )

    if (
        "index.crates.io" not in repository_url
        and "crates.io" not in repository_url
    ):
        raise RepositoryError(
            "Для удалённого режима укажите репозиторий crates.io."
        )


def _is_supported_dependency(dependency: dict[str, Any]) -> bool:
    """Проверяет, нужно ли учитывать зависимость Cargo."""
    if dependency.get("kind") not in SUPPORTED_DEPENDENCY_KINDS:
        return False

    if dependency.get("optional", False):
        return False

    if dependency.get("target") is not None:
        return False

    return isinstance(dependency.get("name"), str)


def _resolve_dependency(
    dependency: dict[str, Any],
) -> dict[str, Any]:
    """Находит подходящую версию зависимости."""
    dependency_name = dependency["name"]
    requirement = dependency.get("req", "*")

    record = _select_version(dependency_name, requirement)

    return {
        "name": dependency_name,
        "version": record["vers"],
        "id": f"{dependency_name}@{record['vers']}",
    }


def _collect_dependencies(
    selected: dict[str, Any],
    depth: int,
    max_depth: int,
    processed: set[str],
    pending: list[tuple[str, str, int]],
) -> list[str]:
    """Собирает зависимости пакета и добавляет их в очередь."""
    dependencies = []
    dependency_ids: set[str] = set()

    if depth >= max_depth:
        return dependencies

    for dependency in selected.get("deps", []):
        if not _is_supported_dependency(dependency):
            continue

        resolved = _resolve_dependency(dependency)
        dependency_id = resolved["id"]

        if dependency_id not in dependency_ids:
            dependency_ids.add(dependency_id)
            dependencies.append(dependency_id)

        if dependency_id not in processed:
            pending.append((
                resolved["name"],
                f"={resolved['version']}",
                depth + 1,
            ))

    return dependencies


def _store_package(
    packages: dict[str, dict[str, Any]],
    package_id: str,
    name: str,
    version: str,
    dependencies: list[str],
) -> None:
    """Сохраняет описание пакета в словарь packages."""
    packages[package_id] = {
        "name": name,
        "version": version,
        "dependencies": dependencies,
    }


def _load_cargo_package(
    current_name: str,
    required_version: str,
    depth: int,
    max_depth: int,
    packages: dict[str, dict[str, Any]],
    processed: set[str],
    pending: list[tuple[str, str, int]],
) -> None:
    """Загружает один пакет и обрабатывает его зависимости."""
    selected = _select_version(current_name, required_version)
    selected_version = selected["vers"]
    package_id = f"{current_name}@{selected_version}"

    if package_id in processed:
        return

    processed.add(package_id)

    dependencies = _collect_dependencies(
        selected,
        depth,
        max_depth,
        processed,
        pending,
    )

    _store_package(
        packages,
        package_id,
        current_name,
        selected_version,
        dependencies,
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
    _validate_cargo_arguments(repository_url, max_depth)

    root_record = _select_version(package_name, f"={version}")
    root_id = f"{package_name}@{root_record['vers']}"

    packages: dict[str, dict[str, Any]] = {}
    pending = [(package_name, f"={version}", 0)]
    processed: set[str] = set()

    while pending:
        current_name, required_version, depth = pending.pop()

        _load_cargo_package(
            current_name,
            required_version,
            depth,
            max_depth,
            packages,
            processed,
            pending,
        )

    if root_id not in packages:
        raise RepositoryError(
            f"Не удалось загрузить корневой пакет '{root_id}'."
        )

    return packages
