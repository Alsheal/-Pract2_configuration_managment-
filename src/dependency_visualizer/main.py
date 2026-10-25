"""Точка входа CLI-приложения."""

import argparse
import sys

from dependency_visualizer.config import ConfigError, load_config


def build_parser() -> argparse.ArgumentParser:
    """Создать парсер аргументов командной строки."""

    parser = argparse.ArgumentParser(
        prog="dependency-visualizer",
        description="Прототип визуализатора графа зависимостей Cargo.",
    )

    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="путь к YAML-конфигурации (по умолчанию: config.yaml)",
    )

    return parser


def main() -> int:
    """Запустить приложение."""

    parser = build_parser()
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except ConfigError as error:
        print(
            f"Ошибка конфигурации: {error}",
            file=sys.stderr,
        )
        return 2

    print("Параметры конфигурации:")
    print(f"package_name: {config.package_name}")
    print(f"repository: {config.repository}")
    print(
        "test_repository_mode: "
        f"{str(config.test_repository_mode).lower()}"
    )
    print(f"version: {config.version}")
    print(f"output_file: {config.output_file}")
    print(f"max_depth: {config.max_depth}")

    print("Этап 1 завершён: конфигурация корректна.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())