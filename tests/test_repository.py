import pytest

from dependency_visualizer.repository import (
    RepositoryError,
    load_repository,
)


def test_load_repository(tmp_path):
    path = tmp_path / "repository.yaml"
    path.write_text(
        """
packages:
  app:
    version: "1.0.0"
    dependencies:
      - lib
  lib:
    version: "2.0.0"
    dependencies: []
""",
        encoding="utf-8",
    )

    packages = load_repository(path)

    assert "app" in packages
    assert packages["app"]["dependencies"] == ["lib"]
    assert packages["lib"]["version"] == "2.0.0"


def test_missing_repository():
    with pytest.raises(RepositoryError, match="не найден"):
        load_repository("missing-repository.yaml")


def test_unknown_dependency(tmp_path):
    path = tmp_path / "repository.yaml"
    path.write_text(
        """
packages:
  app:
    version: "1.0.0"
    dependencies:
      - missing
""",
        encoding="utf-8",
    )

    with pytest.raises(RepositoryError, match="отсутствующего"):
        load_repository(path)


def test_invalid_yaml(tmp_path):
    path = tmp_path / "repository.yaml"
    path.write_text("packages: [", encoding="utf-8")

    with pytest.raises(RepositoryError, match="Некорректный YAML"):
        load_repository(path)
