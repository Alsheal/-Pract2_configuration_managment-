
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


class SVGRenderError(ValueError):
    """Ошибка создания SVG-визуализации."""


SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NAMESPACE)


def _tag(name: str) -> str:
    """Создаёт имя элемента SVG с пространством имён."""
    return f"{{{SVG_NAMESPACE}}}{name}"


def render_graph(
    graph: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Создаёт SVG-изображение направленного графа зависимостей."""
    if not isinstance(graph, dict):
        raise SVGRenderError("Граф должен быть словарём.")

    root_name = graph.get("root")
    nodes = graph.get("nodes")
    edges = graph.get("edges")

    if not isinstance(root_name, str) or not root_name:
        raise SVGRenderError("Не указано имя корневого пакета.")

    if not isinstance(nodes, list) or not nodes:
        raise SVGRenderError("Граф должен содержать список вершин.")

    if not isinstance(edges, list):
        raise SVGRenderError("Граф должен содержать список рёбер.")

    node_map = {}

    for node in nodes:
        if not isinstance(node, dict):
            raise SVGRenderError("Описание вершины должно быть словарём.")

        name = node.get("name")
        version = node.get("version")
        depth = node.get("depth")

        if not isinstance(name, str) or not name:
            raise SVGRenderError("Имя вершины должно быть непустой строкой.")

        if not isinstance(version, str) or not version:
            raise SVGRenderError(
                f"У вершины '{name}' отсутствует версия."
            )

        if (
            not isinstance(depth, int)
            or isinstance(depth, bool)
            or depth < 0
        ):
            raise SVGRenderError(
                f"Некорректная глубина вершины '{name}'."
            )

        if name in node_map:
            raise SVGRenderError(
                f"Обнаружена повторяющаяся вершина '{name}'."
            )

        node_map[name] = node

    if root_name not in node_map:
        raise SVGRenderError("Корневая вершина отсутствует в графе.")

    for edge in edges:
        if not isinstance(edge, dict):
            raise SVGRenderError("Описание ребра должно быть словарём.")

        source = edge.get("source")
        target = edge.get("target")

        if source not in node_map or target not in node_map:
            raise SVGRenderError(
                "Ребро ссылается на отсутствующую вершину."
            )

    node_width = 180
    node_height = 64
    horizontal_gap = 100
    vertical_gap = 45
    margin = 40

    max_depth = max(node["depth"] for node in nodes)

    levels = {}
    for node in nodes:
        levels.setdefault(node["depth"], []).append(node["name"])

    max_level_size = max(len(level) for level in levels.values())

    width = (
        margin * 2
        + (max_depth + 1) * node_width
        + max_depth * horizontal_gap
    )
    height = (
        margin * 2
        + max_level_size * node_height
        + (max_level_size - 1) * vertical_gap
    )

    positions = {}

    for depth, names in levels.items():
        for index, name in enumerate(names):
            x = margin + depth * (node_width + horizontal_gap)
            y = margin + index * (node_height + vertical_gap)

            positions[name] = (
                x,
                y,
                x + node_width / 2,
                y + node_height / 2,
            )

    svg = ET.Element(
        _tag("svg"),
        {
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
            "version": "1.1",
        },
    )

    title = ET.SubElement(svg, _tag("title"))
    title.text = f"Граф зависимостей пакета {root_name}"

    definitions = ET.SubElement(svg, _tag("defs"))

    marker = ET.SubElement(
        definitions,
        _tag("marker"),
        {
            "id": "arrow",
            "markerWidth": "10",
            "markerHeight": "10",
            "refX": "8",
            "refY": "3",
            "orient": "auto",
            "markerUnits": "strokeWidth",
        },
    )

    ET.SubElement(
        marker,
        _tag("path"),
        {
            "d": "M0,0 L0,6 L9,3 z",
            "fill": "#64748b",
        },
    )

    # Сначала рисуем рёбра, чтобы они находились под вершинами.
    for edge in edges:
        source_x, source_y, _, _ = positions[edge["source"]]
        target_x, target_y, _, _ = positions[edge["target"]]

        source_depth = node_map[edge["source"]]["depth"]
        target_depth = node_map[edge["target"]]["depth"]

        if target_depth > source_depth:
            start_x = source_x + node_width
            start_y = source_y + node_height / 2
            end_x = target_x
            end_y = target_y + node_height / 2

            path = (
                f"M {start_x} {start_y} "
                f"L {end_x} {end_y}"
            )
        else:
            # Для обратных рёбер, например при цикле,
            # используем дугу над или под вершинами.
            start_x = source_x + node_width / 2
            start_y = source_y
            end_x = target_x + node_width / 2
            end_y = target_y

            control_y = min(start_y, end_y) - 30

            path = (
                f"M {start_x} {start_y} "
                f"Q {(start_x + end_x) / 2} {control_y} "
                f"{end_x} {end_y}"
            )

        ET.SubElement(
            svg,
            _tag("path"),
            {
                "d": path,
                "fill": "none",
                "stroke": "#64748b",
                "stroke-width": "2",
                "marker-end": "url(#arrow)",
            },
        )

    # Затем рисуем вершины и подписи.
    for node in nodes:
        name = node["name"]
        version = node["version"]
        depth = node["depth"]

        x, y, _, _ = positions[name]

        is_root = name == root_name

        fill = "#dbeafe" if is_root else "#dcfce7"
        stroke = "#3b82f6" if is_root else "#22a06b"
        text_color = "#1e3a8a" if is_root else "#14532d"

        ET.SubElement(
            svg,
            _tag("rect"),
            {
                "x": str(x),
                "y": str(y),
                "width": str(node_width),
                "height": str(node_height),
                "rx": "8",
                "fill": fill,
                "stroke": stroke,
                "stroke-width": "2",
            },
        )

        name_text = ET.SubElement(
            svg,
            _tag("text"),
            {
                "x": str(x + node_width / 2),
                "y": str(y + 25),
                "text-anchor": "middle",
                "font-size": "15",
                "font-weight": "bold",
                "fill": text_color,
            },
        )
        name_text.text = name

        version_text = ET.SubElement(
            svg,
            _tag("text"),
            {
                "x": str(x + node_width / 2),
                "y": str(y + 46),
                "text-anchor": "middle",
                "font-size": "12",
                "fill": text_color,
            },
        )
        version_text.text = f"v{version} | depth {depth}"

    output = Path(output_path)

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(svg).write(
            output,
            encoding="utf-8",
            xml_declaration=True,
        )
    except OSError as exc:
        raise SVGRenderError(
            f"Не удалось сохранить SVG-файл: {exc}"
        ) from exc

    return output
