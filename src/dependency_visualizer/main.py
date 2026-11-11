
"""Точка входа CLI-приложения."""

import argparse
import sys
from pathlib import Path

from dependency_visualizer.config import (
    AppConfig,
    ConfigError,
    load_config,
)
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


def _print_configuration(config: AppConfig) -> None:
    """Вывести параметры загруженной конфигурации."""
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


def _load_packages(config: AppConfig) -> tuple[dict, str]:
    """Загрузить пакеты и определить идентификатор корневого пакета."""
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

    return packages, root_id


def _print_direct_dependencies(
    packages: dict,
    root_id: str,
    package_name: str,
) -> None:
    """Вывести прямые зависимости корневого пакета."""
    dependencies = packages[root_id]["dependencies"]

    print(f"\nПрямые зависимости пакета {package_name}:")

    if not dependencies:
        print("Прямых зависимостей нет.")
        return

    for dependency_id in dependencies:
        dependency = packages[dependency_id]
        name = dependency.get("name", dependency_id)
        print(f"- {name} ({dependency['version']})")


def _print_load_order(graph: dict) -> None:
    """Вывести порядок загрузки или обнаруженные циклы."""
    result = get_dependency_load_order(graph)

    if result["cycles"]:
        _print_cycles(graph, result["cycles"])
        return

    print("\nПорядок загрузки зависимостей:")
    for index, package in enumerate(result["order"], start=1):
        print(f"{index}. {package}")


def _print_cycles(graph: dict, cycles: list) -> None:
    """Вывести циклические связи между пакетами."""
    print(
        "\nОбнаружены циклические зависимости. "
        "Корректный порядок загрузки невозможен:"
    )

    node_map = {
        node["id"]: node
        for node in graph["nodes"]
    }

    for source, target in cycles:
        source_node = node_map[source]
        target_node = node_map[target]

        print(
            f"- {source_node['name']}@{source_node['version']} -> "
            f"{target_node['name']}@{target_node['version']}"
        )


def _render_outputs(
    graph: dict,
    output_file: str,
) -> tuple[Path, Path]:
    """Создать SVG- и Mermaid-представления графа."""
    output_path = render_graph(graph, output_file)
    mermaid_path = Path(output_file).with_suffix(".mmd")
    mermaid_path = render_mermaid(graph, mermaid_path)

    return output_path, mermaid_path


def _run_pipeline(config: AppConfig) -> None:
    """Выполнить этапы загрузки, анализа и визуализации."""
    _print_configuration(config)
    print("\nЭтап 1 завершён: конфигурация корректна.")

    packages, root_id = _load_packages(config)

    print("\nЭтап 2 завершён: репозиторий загружен.")
    print(f"Количество пакетов: {len(packages)}")
    _print_direct_dependencies(
        packages,
        root_id,
        config.package_name,
    )

    analysis = analyze_dependencies(
        packages,
        root_id,
        config.max_depth,
    )

    print("\nЭтап 3 завершён: анализ зависимостей выполнен.")
    print(f"Найдено транзитивных зависимостей: {len(analysis)}")

    graph = build_dependency_graph(
        packages,
        root_id,
        config.max_depth,
    )

    print("\nЭтап 4 завершён: граф зависимостей построен.")
    print(f"Количество вершин: {len(graph['nodes'])}")
    print(f"Количество рёбер: {len(graph['edges'])}")
    _print_load_order(graph)

    output_path, mermaid_path = _render_outputs(
        graph,
        config.output_file,
    )

    print("\nЭтап 5 завершён: визуализации созданы.")
    print(f"SVG-файл сохранён: {output_path.resolve()}")
    print(f"Mermaid-файл сохранён: {mermaid_path.resolve()}")


def main() -> int:
    """Запустить приложение и обработать ошибки выполнения."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        _run_pipeline(config)
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
