"""Создание SVG- и Mermaid-визуализаций графа зависимостей."""

from pathlib import Path
from typing import Any
from xml.etree.ElementTree import (
    Element,
    ElementTree as et_tree,
    SubElement,
    register_namespace,
)


NODE_WIDTH = 180
NODE_HEIGHT = 64
HORIZONTAL_GAP = 100
VERTICAL_GAP = 45
MARGIN = 40
ARROW_OFFSET = 30

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ARROW_COLOR = "#64748b"
ROOT_FILL = "#dbeafe"
ROOT_STROKE = "#3b82f6"
ROOT_TEXT = "#1e3a8a"
DEPENDENCY_FILL = "#dcfce7"
DEPENDENCY_STROKE = "#22a06b"
DEPENDENCY_TEXT = "#14532d"

FONT_NAME_SIZE = 15
FONT_VERSION_SIZE = 12
STROKE_WIDTH = 2
CORNER_RADIUS = 8

NAME_TEXT_OFFSET = 25
VERSION_TEXT_OFFSET = 46

MERMAID_DIRECTION = "flowchart LR"
MERMAID_NODE_PREFIX = "node_"

ARROW_MARKER_WIDTH = 10
ARROW_MARKER_HEIGHT = 10
ARROW_MARKER_REF_X = 8
ARROW_MARKER_REF_Y = 3
ARROW_MARKER_PATH = "M0,0 L0,6 L9,3 z"

register_namespace("", SVG_NAMESPACE)


class SVGRenderError(ValueError):
    """Ошибка создания визуализации."""


def _tag(name: str) -> str:
    """Возвращает имя SVG-элемента с пространством имён."""
    return f"{{{SVG_NAMESPACE}}}{name}"


def _require_string(value: Any, message: str) -> str:
    """Проверяет, что значение — непустая строка."""
    if not isinstance(value, str) or not value:
        raise SVGRenderError(message)
    return value


def _require_depth(node: dict[str, Any], name: str) -> None:
    """Проверяет корректность поля depth у вершины."""
    depth = node.get("depth")

    if (
        not isinstance(depth, int)
        or isinstance(depth, bool)
        or depth < 0
    ):
        raise SVGRenderError(
            f"Некорректная глубина вершины '{name}'."
        )


def _validate_node(
    node: Any,
    check_depth: bool,
) -> tuple[str, str, str]:
    """Проверяет описание одной вершины и возвращает её поля."""
    if not isinstance(node, dict):
        raise SVGRenderError(
            "Описание вершины должно быть словарём."
        )

    node_id = _require_string(
        node.get("id", node.get("name")),
        "Некорректный идентификатор вершины.",
    )
    name = _require_string(
        node.get("name"),
        "Некорректное имя вершины.",
    )
    version = _require_string(
        node.get("version"),
        f"У вершины '{name}' отсутствует версия.",
    )

    if check_depth:
        _require_depth(node, name)

    return node_id, name, version


def _validate_edge(
    edge: Any,
    node_map: dict[str, dict[str, Any]],
) -> None:
    """Проверяет одно ребро графа."""
    if not isinstance(edge, dict):
        raise SVGRenderError(
            "Описание ребра должно быть словарём."
        )

    source = edge.get("source")
    target = edge.get("target")

    if (
        not isinstance(source, str)
        or not isinstance(target, str)
        or source not in node_map
        or target not in node_map
    ):
        raise SVGRenderError(
            "Ребро ссылается на отсутствующую вершину."
        )


def _validate_root_field(graph: dict[str, Any]) -> str:
    """Проверяет поле root графа."""
    root_id = graph.get("root")

    if not isinstance(root_id, str) or not root_id:
        raise SVGRenderError(
            "Не указан идентификатор корневого пакета."
        )

    return root_id


def _validate_lists_field(graph: dict[str, Any]) -> tuple[list, list]:
    """Проверяет поля nodes и edges графа."""
    nodes = graph.get("nodes")
    edges = graph.get("edges")

    if not isinstance(nodes, list) or not nodes:
        raise SVGRenderError(
            "Граф должен содержать список вершин."
        )

    if not isinstance(edges, list):
        raise SVGRenderError(
            "Граф должен содержать список рёбер."
        )

    return nodes, edges


def _collect_node_map(
    nodes: list,
    check_depth: bool,
) -> dict[str, dict[str, Any]]:
    """Собирает карту вершин с проверкой дубликатов."""
    node_map: dict[str, dict[str, Any]] = {}

    for node in nodes:
        node_id, _, _ = _validate_node(node, check_depth)

        if node_id in node_map:
            raise SVGRenderError(
                f"Обнаружена повторяющаяся вершина '{node_id}'."
            )

        node_map[node_id] = node

    return node_map


def _validate_graph(
    graph: dict[str, Any],
    check_depth: bool = False,
) -> tuple[str, dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Проверяет структуру графа, вершины и рёбра."""
    if not isinstance(graph, dict):
        raise SVGRenderError("Граф должен быть словарём.")

    root_id = _validate_root_field(graph)
    nodes, edges = _validate_lists_field(graph)
    node_map = _collect_node_map(nodes, check_depth)

    if root_id not in node_map:
        raise SVGRenderError(
            "Корневая вершина отсутствует в графе."
        )

    for edge in edges:
        _validate_edge(edge, node_map)

    return root_id, node_map, edges


def _calculate_layout(
    node_map: dict[str, dict[str, Any]],
) -> tuple[dict[str, tuple[int, int]], int, int]:
    """Рассчитывает координаты вершин и размеры изображения."""
    levels: dict[int, list[str]] = {}

    for node_id, node in node_map.items():
        levels.setdefault(node["depth"], []).append(node_id)

    positions: dict[str, tuple[int, int]] = {}

    for depth, node_ids in levels.items():
        for index, node_id in enumerate(node_ids):
            x = MARGIN + depth * (NODE_WIDTH + HORIZONTAL_GAP)
            y = MARGIN + index * (NODE_HEIGHT + VERTICAL_GAP)
            positions[node_id] = (x, y)

    max_depth = max(levels)
    max_level_size = max(len(level) for level in levels.values())

    width = (
        MARGIN * 2
        + (max_depth + 1) * NODE_WIDTH
        + max_depth * HORIZONTAL_GAP
    )
    height = (
        MARGIN * 2
        + max_level_size * NODE_HEIGHT
        + (max_level_size - 1) * VERTICAL_GAP
    )

    return positions, width, height


def _forward_edge_path(
    source_pos: tuple[int, int],
    target_pos: tuple[int, int],
) -> str:
    """Формирует путь для ребра между соседними уровнями."""
    source_x, source_y = source_pos
    target_x, target_y = target_pos

    start_x = source_x + NODE_WIDTH
    start_y = source_y + NODE_HEIGHT // 2
    end_x = target_x
    end_y = target_y + NODE_HEIGHT // 2

    return f"M {start_x} {start_y} L {end_x} {end_y}"


def _back_edge_path(
    source_pos: tuple[int, int],
    target_pos: tuple[int, int],
) -> str:
    """Формирует путь для обратного/циклического ребра."""
    source_x, source_y = source_pos
    target_x, target_y = target_pos

    start_x = source_x + NODE_WIDTH // 2
    start_y = source_y
    end_x = target_x + NODE_WIDTH // 2
    end_y = target_y
    control_y = min(start_y, end_y) - ARROW_OFFSET

    return (
        f"M {start_x} {start_y} "
        f"Q {(start_x + end_x) / 2} {control_y} "
        f"{end_x} {end_y}"
    )


def _draw_edges(
    svg: Element,
    edges: list[dict[str, Any]],
    positions: dict[str, tuple[int, int]],
    node_map: dict[str, dict[str, Any]],
) -> None:
    """Рисует направленные рёбра между вершинами."""
    for edge in edges:
        source = edge["source"]
        target = edge["target"]

        source_pos = positions[source]
        target_pos = positions[target]

        if node_map[target]["depth"] > node_map[source]["depth"]:
            path = _forward_edge_path(source_pos, target_pos)
        else:
            path = _back_edge_path(source_pos, target_pos)

        SubElement(
            svg,
            _tag("path"),
            {
                "d": path,
                "fill": "none",
                "stroke": ARROW_COLOR,
                "stroke-width": str(STROKE_WIDTH),
                "marker-end": "url(#arrow)",
            },
        )


def _node_colors(
    node_id: str,
    root_id: str,
) -> tuple[str, str, str]:
    """Возвращает цвета оформления вершины."""
    if node_id == root_id:
        return ROOT_FILL, ROOT_STROKE, ROOT_TEXT

    return DEPENDENCY_FILL, DEPENDENCY_STROKE, DEPENDENCY_TEXT


def _draw_node_rect(
    svg: Element,
    position: tuple[int, int],
    fill: str,
    stroke: str,
) -> None:
    """Рисует прямоугольник вершины."""
    x, y = position

    SubElement(
        svg,
        _tag("rect"),
        {
            "x": str(x),
            "y": str(y),
            "width": str(NODE_WIDTH),
            "height": str(NODE_HEIGHT),
            "rx": str(CORNER_RADIUS),
            "fill": fill,
            "stroke": stroke,
            "stroke-width": str(STROKE_WIDTH),
        },
    )


def _draw_node_labels(
    svg: Element,
    node: dict[str, Any],
    position: tuple[int, int],
    text_color: str,
) -> None:
    """Рисует подписи имени и версии вершины."""
    x, y = position
    center_x = x + NODE_WIDTH // 2

    labels = (
        (node["name"], NAME_TEXT_OFFSET, FONT_NAME_SIZE),
        (
            f"v{node['version']} | depth {node['depth']}",
            VERSION_TEXT_OFFSET,
            FONT_VERSION_SIZE,
        ),
    )

    for text, offset, font_size in labels:
        element = SubElement(
            svg,
            _tag("text"),
            {
                "x": str(center_x),
                "y": str(y + offset),
                "text-anchor": "middle",
                "font-size": str(font_size),
                "fill": text_color,
            },
        )
        element.text = text


def _draw_nodes(
    svg: Element,
    node_map: dict[str, dict[str, Any]],
    root_id: str,
    positions: dict[str, tuple[int, int]],
) -> None:
    """Рисует вершины графа и их подписи."""
    for node_id, node in node_map.items():
        position = positions[node_id]
        fill, stroke, text_color = _node_colors(node_id, root_id)

        _draw_node_rect(svg, position, fill, stroke)
        _draw_node_labels(svg, node, position, text_color)


def _save_file(
    output_path: str | Path,
    content: str | Element,
) -> Path:
    """Сохраняет текстовый или SVG-файл."""
    output = Path(output_path)

    try:
        output.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, str):
            output.write_text(content, encoding="utf-8")
        else:
            et_tree(content).write(
                output,
                encoding="utf-8",
                xml_declaration=True,
            )
    except OSError as exc:
        raise SVGRenderError(
            f"Не удалось сохранить файл: {exc}"
        ) from exc

    return output


def _create_svg_root(width: int, height: int) -> Element:
    """Создаёт корневой SVG-элемент."""
    return Element(
        _tag("svg"),
        {
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
            "version": "1.1",
        },
    )


def _add_title(
    svg: Element,
    node_map: dict[str, dict[str, Any]],
    root_id: str,
) -> None:
    """Добавляет заголовок SVG."""
    title = SubElement(svg, _tag("title"))
    title.text = (
        f"Граф зависимостей пакета {node_map[root_id]['name']}"
    )


def _add_arrow_marker(svg: Element) -> None:
    """Добавляет маркер стрелки в defs."""
    definitions = SubElement(svg, _tag("defs"))
    marker = SubElement(
        definitions,
        _tag("marker"),
        {
            "id": "arrow",
            "markerWidth": str(ARROW_MARKER_WIDTH),
            "markerHeight": str(ARROW_MARKER_HEIGHT),
            "refX": str(ARROW_MARKER_REF_X),
            "refY": str(ARROW_MARKER_REF_Y),
            "orient": "auto",
        },
    )

    SubElement(
        marker,
        _tag("path"),
        {
            "d": ARROW_MARKER_PATH,
            "fill": ARROW_COLOR,
        },
    )


def render_graph(
    graph: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Создаёт SVG-изображение графа зависимостей."""
    root_id, node_map, edges = _validate_graph(
        graph,
        check_depth=True,
    )
    positions, width, height = _calculate_layout(node_map)

    svg = _create_svg_root(width, height)
    _add_title(svg, node_map, root_id)
    _add_arrow_marker(svg)

    _draw_edges(svg, edges, positions, node_map)
    _draw_nodes(svg, node_map, root_id, positions)

    return _save_file(output_path, svg)


def render_mermaid(
    graph: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Создаёт текстовое представление графа в формате Mermaid."""
    _, node_map, edges = _validate_graph(graph)

    mermaid_ids = {
        node_id: f"{MERMAID_NODE_PREFIX}{index}"
        for index, node_id in enumerate(node_map)
    }

    lines = [MERMAID_DIRECTION]

    for node_id, node in node_map.items():
        name = node["name"].replace('"', "'")
        version = node["version"].replace('"', "'")
        lines.append(
            f'    {mermaid_ids[node_id]}["{name} v{version}"]'
        )

    for edge in edges:
        lines.append(
            f"    {mermaid_ids[edge['source']]} "
            f"--> {mermaid_ids[edge['target']]}"
        )

    return _save_file(output_path, "\n".join(lines) + "\n")
