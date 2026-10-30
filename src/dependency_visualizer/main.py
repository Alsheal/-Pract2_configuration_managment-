
"""Точка входа CLI-приложения."""

import argparse
import sys

from dependency_visualizer.config import ConfigError, load_config
from dependency_visualizer.repository import RepositoryError, load_repository
from dependency_visualizer.analyzer import analyze_dependencies
from dependency_visualizer.graph import DependencyGraphError, build_dependency_graph
from dependency_visualizer.renderer import SVGRenderError, render_graph


def build_parser() -> argparse.ArgumentParser:
    """Создать парсер аргументов командной строки."""

    parser = argparse.ArgumentParser(
        prog="dependency-visualizer",
        description="Визуализатор графа зависимостей Cargo.",
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
        # Этап 1. Загрузка конфигурации
        config = load_config(args.config)

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

        print("\nЭтап 1 завершён: конфигурация корректна.")

        # Этап 2. Загрузка репозитория
        packages = load_repository(config.repository)

        print("\nЭтап 2 завершён: репозиторий загружен.")
        print(f"Количество пакетов: {len(packages)}")

        # Этап 3. Анализ зависимостей
        analysis = analyze_dependencies(
            packages,
            config.package_name,
            config.max_depth,
        )

        print("\nЭтап 3 завершён: анализ зависимостей выполнен.")

        # Этап 4. Построение графа
        graph = build_dependency_graph(
            packages,
            config.package_name,
            config.max_depth,
        )

        print("\nЭтап 4 завершён: граф зависимостей построен.")
        print(f"Количество вершин: {len(graph['nodes'])}")
        print(f"Количество рёбер: {len(graph['edges'])}")

        # Этап 5. SVG-визуализация
        output_path = render_graph(
            graph,
            config.output_file,
        )

        print("\nЭтап 5 завершён: SVG-визуализация создана.")
        print(f"Файл сохранён: {output_path.resolve()}")

        return 0

    except ConfigError as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return 2

    except (
        RepositoryError,
        DependencyGraphError,
        SVGRenderError,
    ) as error:
        print(f"Ошибка выполнения: {error}", file=sys.stderr)
        return 1

    except OSError as error:
        print(f"Ошибка работы с файлами: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
