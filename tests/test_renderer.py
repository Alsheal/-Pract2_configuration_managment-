
import xml.etree.ElementTree as ET

import pytest

from dependency_visualizer.renderer import (
    SVGRenderError,
    render_graph,
)


@pytest.fixture
def graph():
    return {
        "root": "serde",
        "nodes": [
            {
                "name": "serde",
                "version": "1.0.0",
                "depth": 0,
            },
            {
                "name": "syn",
                "version": "2.0.0",
                "depth": 1,
            },
            {
                "name": "quote",
                "version": "1.0.0",
                "depth": 1,
            },
            {
                "name": "unicode-ident",
                "version": "1.0.0",
                "depth": 2,
            },
        ],
        "edges": [
            {"source": "serde", "target": "syn"},
            {"source": "serde", "target": "quote"},
            {"source": "syn", "target": "unicode-ident"},
        ],
    }


def test_render_graph_creates_svg_file(graph, tmp_path):
    output = tmp_path / "dependencies.svg"

    result = render_graph(graph, output)

    assert result == output
    assert output.is_file()


def test_render_graph_creates_valid_xml(graph, tmp_path):
    output = tmp_path / "dependencies.svg"

    render_graph(graph, output)

    tree = ET.parse(output)

    assert tree.getroot().tag.endswith("svg")


def test_svg_contains_all_package_names(graph, tmp_path):
    output = tmp_path / "dependencies.svg"

    render_graph(graph, output)

    content = output.read_text(encoding="utf-8")

    assert "serde" in content
    assert "syn" in content
    assert "quote" in content
    assert "unicode-ident" in content


def test_svg_contains_package_versions(graph, tmp_path):
    output = tmp_path / "dependencies.svg"

    render_graph(graph, output)

    content = output.read_text(encoding="utf-8")

    assert "1.0.0" in content
    assert "2.0.0" in content


def test_svg_contains_edges(graph, tmp_path):
    output = tmp_path / "dependencies.svg"

    render_graph(graph, output)

    content = output.read_text(encoding="utf-8")

    assert "marker-end" in content
    assert content.count("<path") == 4


def test_svg_contains_depth_information(graph, tmp_path):
    output = tmp_path / "dependencies.svg"

    render_graph(graph, output)

    content = output.read_text(encoding="utf-8")

    assert "depth 0" in content
    assert "depth 1" in content
    assert "depth 2" in content


def test_render_graph_creates_parent_directory(graph, tmp_path):
    output = tmp_path / "nested" / "result.svg"

    render_graph(graph, output)

    assert output.is_file()


def test_render_graph_rejects_empty_nodes(tmp_path):
    invalid_graph = {
        "root": "serde",
        "nodes": [],
        "edges": [],
    }

    with pytest.raises(SVGRenderError):
        render_graph(invalid_graph, tmp_path / "result.svg")


def test_render_graph_rejects_missing_root(tmp_path):
    invalid_graph = {
        "root": "serde",
        "nodes": [
            {
                "name": "syn",
                "version": "2.0.0",
                "depth": 1,
            }
        ],
        "edges": [],
    }

    with pytest.raises(SVGRenderError):
        render_graph(invalid_graph, tmp_path / "result.svg")


def test_render_graph_rejects_invalid_edge(graph, tmp_path):
    graph["edges"].append(
        {"source": "serde", "target": "missing"}
    )

    with pytest.raises(SVGRenderError):
        render_graph(graph, tmp_path / "result.svg")


def test_render_graph_rejects_duplicate_nodes(tmp_path):
    invalid_graph = {
        "root": "serde",
        "nodes": [
            {
                "name": "serde",
                "version": "1.0.0",
                "depth": 0,
            },
            {
                "name": "serde",
                "version": "2.0.0",
                "depth": 1,
            },
        ],
        "edges": [],
    }

    with pytest.raises(SVGRenderError):
        render_graph(invalid_graph, tmp_path / "result.svg")


def test_render_graph_escapes_special_characters(tmp_path):
    special_graph = {
        "root": "lib&core",
        "nodes": [
            {
                "name": "lib&core",
                "version": "1.0.0",
                "depth": 0,
            }
        ],
        "edges": [],
    }

    output = tmp_path / "special.svg"

    render_graph(special_graph, output)

    tree = ET.parse(output)

    tree = ET.parse(output)

    assert tree.getroot().tag.endswith("svg")

    text_values = [
        element.text
        for element in tree.getroot().iter()
        if element.text
    ]

    assert "lib&core" in text_values