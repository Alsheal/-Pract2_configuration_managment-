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


def load_config(config_path: str | Path) -> AppConfig:
    """Загрузить конфигурацию из YAML и проверить её."""

    path = Path(config_path).expanduser()

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

    # 1. Имя пакета
    package_name = data["package_name"]

    if (
        not isinstance(package_name, str)
        or not PACKAGE_NAME_RE.fullmatch(package_name.strip())
    ):
        raise ConfigError(
            "package_name: укажите имя из букв, цифр, '-' или '_'."
        )

    package_name = package_name.strip()

    # 2. URL или путь к тестовому репозиторию
    repository = data["repository"]

    if not isinstance(repository, str) or not repository.strip():
        raise ConfigError(
            "repository: значение должно быть непустой строкой."
        )

    repository = repository.strip()

    # 3. Режим тестового репозитория
    test_mode = data["test_repository_mode"]

    if not isinstance(test_mode, bool):
        raise ConfigError(
            "test_repository_mode: допустимы только true или false."
        )

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
            parsed_url.scheme not in {"http", "https", "git", "ssh"}
            or not parsed_url.netloc
        ):
            raise ConfigError(
                "repository: укажите абсолютный URL "
                "с поддерживаемой схемой: http, https, git или ssh."
            )

    # 4. Версия пакета
    version = data["version"]

    if (
        not isinstance(version, str)
        or not VERSION_RE.fullmatch(version.strip())
    ):
        raise ConfigError(
            "version: ожидается версия SemVer, например 1.2.3."
        )

    version = version.strip().removeprefix("v")

    # 5. Имя выходного SVG-файла
    output_file = data["output_file"]

    if not isinstance(output_file, str) or not output_file.strip():
        raise ConfigError(
            "output_file: укажите имя выходного файла."
        )

    output_file = output_file.strip()

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

    # 6. Максимальная глубина анализа
    max_depth = data["max_depth"]

    if (
        isinstance(max_depth, bool)
        or not isinstance(max_depth, int)
        or max_depth < 0
    ):
        raise ConfigError(
            "max_depth: требуется целое число, не меньшее нуля."
        )

    return AppConfig(
        package_name=package_name,
        repository=repository,
        test_repository_mode=test_mode,
        version=version,
        output_file=output_file,
        max_depth=max_depth,
    )