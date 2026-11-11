
"""Загрузка и проверка YAML-конфигурации."""

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse

import yaml


REQUIRED_KEYS = {
    "package_name",
    "repository",
    "test_repository_mode",
    "version",
    "output_file",
    "max_depth",
}

PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
VERSION_RE = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
SUPPORTED_SCHEMES = {"http", "https", "git", "ssh"}


class ConfigError(ValueError):
    """Ошибка загрузки или проверки конфигурации."""


@dataclass(frozen=True)
class AppConfig:
    """Параметры приложения."""

    package_name: str
    repository: str
    test_repository_mode: bool
    version: str
    output_file: str
    max_depth: int


def _read_yaml(path: Path) -> dict:
    """Прочитать YAML-файл и проверить тип корневого объекта."""
    if not path.exists():
        raise ConfigError(
            f"Конфигурационный файл не найден: {path}"
        )

    if not path.is_file():
        raise ConfigError(
            f"Путь конфигурации не является файлом: {path}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except yaml.YAMLError as error:
        raise ConfigError(
            f"Некорректный YAML: {error}"
        ) from error
    except OSError as error:
        raise ConfigError(
            f"Не удалось прочитать конфигурацию: {error}"
        ) from error

    if not isinstance(data, dict):
        raise ConfigError(
            "Конфигурация должна содержать YAML-объект."
        )

    return data


def _validate_keys(data: dict) -> None:
    """Проверить наличие обязательных и отсутствие лишних ключей."""
    missing = REQUIRED_KEYS - data.keys()
    extra = data.keys() - REQUIRED_KEYS

    if missing:
        raise ConfigError(
            "Отсутствуют обязательные параметры: "
            + ", ".join(sorted(missing))
        )

    if extra:
        raise ConfigError(
            "Неизвестные параметры: "
            + ", ".join(sorted(extra))
        )


def _validate_package_name(value: object) -> str:
    """Проверить и вернуть имя пакета."""
    if (
        not isinstance(value, str)
        or not PACKAGE_NAME_RE.fullmatch(value.strip())
    ):
        raise ConfigError(
            "package_name: укажите имя из букв, цифр, '-' или '_'."
        )

    return value.strip()


def _validate_repository(value: object, test_mode: bool) -> str:
    """Проверить URL репозитория или путь к тестовому файлу."""
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(
            "repository: значение должно быть непустой строкой."
        )

    repository = value.strip()

    if test_mode:
        repo_path = Path(repository).expanduser()

        if not repo_path.exists():
            raise ConfigError(
                f"repository: тестовый файл не найден: {repo_path}"
            )

        if not repo_path.is_file():
            raise ConfigError(
                "repository: в тестовом режиме нужен путь к файлу."
            )
    else:
        parsed_url = urlparse(repository)

        if (
            parsed_url.scheme not in SUPPORTED_SCHEMES
            or not parsed_url.netloc
        ):
            raise ConfigError(
                "repository: укажите абсолютный URL "
                "с поддерживаемой схемой: http, https, git или ssh."
            )

    return repository


def _validate_test_mode(value: object) -> bool:
    """Проверить флаг тестового режима."""
    if not isinstance(value, bool):
        raise ConfigError(
            "test_repository_mode: допустимы только true или false."
        )

    return value


def _validate_version(value: object) -> str:
    """Проверить и нормализовать версию пакета."""
    if (
        not isinstance(value, str)
        or not VERSION_RE.fullmatch(value.strip())
    ):
        raise ConfigError(
            "version: ожидается версия SemVer, например 1.2.3."
        )

    return value.strip().removeprefix("v")


def _validate_output_file(value: object) -> str:
    """Проверить имя выходного SVG-файла."""
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(
            "output_file: укажите имя выходного файла."
        )

    output_file = value.strip()

    if (
        Path(output_file).name != output_file
        or output_file in {".", ".."}
    ):
        raise ConfigError(
            "output_file: укажите имя файла без пути к каталогу."
        )

    if Path(output_file).suffix.lower() != ".svg":
        raise ConfigError(
            "output_file: расширение файла должно быть .svg."
        )

    return output_file


def _validate_max_depth(value: object) -> int:
    """Проверить максимальную глубину анализа."""
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise ConfigError(
            "max_depth: требуется целое число, не меньшее нуля."
        )

    return value


def load_config(config_path: str | Path) -> AppConfig:
    """Загрузить конфигурацию из YAML и проверить её."""
    path = Path(config_path).expanduser()
    data = _read_yaml(path)
    _validate_keys(data)

    test_mode = _validate_test_mode(
        data["test_repository_mode"]
    )

    return AppConfig(
        package_name=_validate_package_name(data["package_name"]),
        repository=_validate_repository(data["repository"], test_mode),
        test_repository_mode=test_mode,
        version=_validate_version(data["version"]),
        output_file=_validate_output_file(data["output_file"]),
        max_depth=_validate_max_depth(data["max_depth"]),
    )
