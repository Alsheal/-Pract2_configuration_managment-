import pytest

from dependency_visualizer.analyzer import (
    DependencyAnalysisError,
    analyze_dependencies,
)


@pytest.fixture
def packages():
    return {
        "serde": {
            "version": "1.0.0",
            "dependencies": ["syn", "quote"],
        },
        "syn": {
            "version": "2.0.0",
            "dependencies": ["unicode-ident"],
        },
        "quote": {
            "version": "1.0.0",
            "dependencies": [],
        },
        "unicode-ident": {
            "version": "1.0.0",
            "dependencies": [],
        },
    }


def test_analyze_direct_and_transitive_dependencies(packages):
    result = analyze_dependencies(packages, "serde", 3)

    names = {item["name"] for item in result}

    assert names == {"syn", "quote", "unicode-ident"}


def test_max_depth_one(packages):
    result = analyze_dependencies(packages, "serde", 1)

    names = {item["name"] for item in result}

    assert names == {"syn", "quote"}


def test_max_depth_zero(packages):
    result = analyze_dependencies(packages, "serde", 0)

    assert result == []


def test_dependency_depth(packages):
    result = analyze_dependencies(packages, "serde", 3)

    depths = {item["name"]: item["depth"] for item in result}

    assert depths["syn"] == 1
    assert depths["quote"] == 1
    assert depths["unicode-ident"] == 2


def test_missing_package(packages):
    with pytest.raises(DependencyAnalysisError, match="не найден"):
        analyze_dependencies(packages, "unknown", 3)


def test_negative_max_depth(packages):
    with pytest.raises(DependencyAnalysisError, match="отрицательным"):
        analyze_dependencies(packages, "serde", -1)


def test_cycle_does_not_loop_forever():
    cyclic_packages = {
        "a": {"version": "1.0", "dependencies": ["b"]},
        "b": {"version": "1.0", "dependencies": ["a"]},
    }

    result = analyze_dependencies(cyclic_packages, "a", 10)

    assert [item["name"] for item in result] == ["b"]
