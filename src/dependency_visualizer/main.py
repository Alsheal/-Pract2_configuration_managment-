"""Точка входа CLI-приложения."""
from pathlib import Path
import argparse
import sys

from matplotlib.path import Path

from dependency_visualizer.config import ConfigError, load_config
from dependency_visualizer.repository import (
    RepositoryError,
    load_repository,
    load_cargo_repository,
)
from dependency_visualizer.analyzer import (
    DependencyAnalysisError,
    analyze_dependencies,
)
from dependency_visualizer.graph import (
    DependencyGraphError,
    build_dependency_graph,
    get_dependency_load_order,
)
from dependency_visualizer.renderer import (
    SVGRenderError,
    render_graph,
    render_mermaid,
)


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

        # Этап 2. Загрузка репозитория.
        if config.test_repository_mode:
            packages = load_repository(config.repository)
            root_id = config.package_name
        else:
            packages = load_cargo_repository(
                config.repository,
                config.package_name,
                config.version,
                config.max_depth,
            )
            root_id = f"{config.package_name}@{config.version}"

        if root_id not in packages:
            raise RepositoryError(
                f"Корневой пакет '{root_id}' не найден."
            )

        print("\nЭтап 2 завершён: репозиторий загружен.")
        print(f"Количество пакетов: {len(packages)}")

        direct_dependencies = packages[root_id]["dependencies"]

        print(f"\nПрямые зависимости пакета {config.package_name}:")
        if direct_dependencies:
            for dependency_id in direct_dependencies:
                dependency = packages[dependency_id]
                name = dependency.get("name", dependency_id)
                print(f"- {name} ({dependency['version']})")
        else:
            print("Прямых зависимостей нет.")

        # Этап 3. Анализ зависимостей.
        analysis = analyze_dependencies(
            packages,
            root_id,
            config.max_depth,
        )

        print("\nЭтап 3 завершён: анализ зависимостей выполнен.")
        print(f"Найдено транзитивных зависимостей: {len(analysis)}")

        # Этап 4. Построение графа и порядка загрузки.
        graph = build_dependency_graph(
            packages,
            root_id,
            config.max_depth,
        )

        print("\nЭтап 4 завершён: граф зависимостей построен.")
        print(f"Количество вершин: {len(graph['nodes'])}")
        print(f"Количество рёбер: {len(graph['edges'])}")

        load_result = get_dependency_load_order(graph)

        if load_result["cycles"]:
            print(
                "\nОбнаружены циклические зависимости. "
                "Корректный порядок загрузки невозможен:"
            )

            node_map = {
                node["id"]: node
                for node in graph["nodes"]
            }

            for source, target in load_result["cycles"]:
                source_name = node_map[source]["name"]
                source_version = node_map[source]["version"]
                target_name = node_map[target]["name"]
                target_version = node_map[target]["version"]

                print(
                    f"- {source_name}@{source_version} -> "
                    f"{target_name}@{target_version}"
                )
        else:
            print("\nПорядок загрузки зависимостей:")
            for index, package in enumerate(
                load_result["order"],
                start=1,
            ):
                print(f"{index}. {package}")

        # Этап 5. SVG- и Mermaid-визуализация.
        output_path = render_graph(
            graph,
            config.output_file,
        )

        mermaid_path = Path(config.output_file).with_suffix(".mmd")
        mermaid_path = render_mermaid(
            graph,
            mermaid_path,
        )

        print("\nЭтап 5 завершён: визуализации созданы.")
        print(f"SVG-файл сохранён: {output_path.resolve()}")
        print(f"Mermaid-файл сохранён: {mermaid_path.resolve()}")

        return 0

    except ConfigError as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return 2

    except (
        RepositoryError,
        DependencyAnalysisError,
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
