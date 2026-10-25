from pathlib import Path

import pytest
import yaml

from dependency_visualizer.config import ConfigError, load_config


def valid_config(repository: str, test_mode: bool = True) -> dict:
    return {
        "package_name": "serde",
        "repository": repository,
        "test_repository_mode": test_mode,
        "version": "1.0.0",
        "output_file": "dependencies.svg",
        "max_depth": 3,
    }


def write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )
    return path


def test_valid_test_config(tmp_path):
    repository = tmp_path / "repository.yaml"
    repository.write_text("A: []\n", encoding="utf-8")

    config_path = write_config(
        tmp_path,
        valid_config(str(repository)),
    )

    config = load_config(config_path)

    assert config.package_name == "serde"
    assert config.test_repository_mode is True
    assert config.max_depth == 3


def test_valid_remote_config(tmp_path):
    data = valid_config(
        "https://github.com/serde-rs/serde",
        False,
    )

    config = load_config(write_config(tmp_path, data))

    assert config.repository == "https://github.com/serde-rs/serde"


def test_missing_config_file(tmp_path):
    with pytest.raises(ConfigError, match="не найден"):
        load_config(tmp_path / "missing.yaml")


def test_malformed_yaml(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "package_name: [unterminated",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="YAML"):
        load_config(path)


def test_missing_parameter(tmp_path):
    data = valid_config("https://example.com/repo", False)
    del data["version"]

    with pytest.raises(ConfigError, match="version"):
        load_config(write_config(tmp_path, data))


def test_unknown_parameter(tmp_path):
    data = valid_config("https://example.com/repo", False)
    data["unexpected"] = 1

    with pytest.raises(ConfigError, match="Неизвестные"):
        load_config(write_config(tmp_path, data))


@pytest.mark.parametrize(
    "value",
    ["", "two words", "bad/name", None],
)
def test_invalid_package_name(tmp_path, value):
    data = valid_config("https://example.com/repo", False)
    data["package_name"] = value

    with pytest.raises(ConfigError, match="package_name"):
        load_config(write_config(tmp_path, data))


@pytest.mark.parametrize("value", ["", None, 42])
def test_invalid_repository(tmp_path, value):
    data = valid_config("https://example.com/repo", False)
    data["repository"] = value

    with pytest.raises(ConfigError, match="repository"):
        load_config(write_config(tmp_path, data))


def test_invalid_repository_url(tmp_path):
    data = valid_config("not-a-url", False)

    with pytest.raises(ConfigError, match="URL"):
        load_config(write_config(tmp_path, data))


def test_missing_test_repository(tmp_path):
    data = valid_config(
        str(tmp_path / "missing-repository.yaml"),
        True,
    )

    with pytest.raises(ConfigError, match="не найден"):
        load_config(write_config(tmp_path, data))


@pytest.mark.parametrize("value", ["true", 1, None])
def test_invalid_test_mode(tmp_path, value):
    data = valid_config("https://example.com/repo", False)
    data["test_repository_mode"] = value

    with pytest.raises(ConfigError, match="test_repository_mode"):
        load_config(write_config(tmp_path, data))


@pytest.mark.parametrize(
    "value",
    ["latest", "1.2", "", None, "01.2.3"],
)
def test_invalid_version(tmp_path, value):
    data = valid_config("https://example.com/repo", False)
    data["version"] = value

    with pytest.raises(ConfigError, match="version"):
        load_config(write_config(tmp_path, data))


@pytest.mark.parametrize(
    "value",
    ["", "../graph.svg", "graph.png", None],
)
def test_invalid_output_file(tmp_path, value):
    data = valid_config("https://example.com/repo", False)
    data["output_file"] = value

    with pytest.raises(ConfigError, match="output_file"):
        load_config(write_config(tmp_path, data))


@pytest.mark.parametrize(
    "value",
    [-1, 1.5, "3", True, None],
)
def test_invalid_max_depth(tmp_path, value):
    data = valid_config("https://example.com/repo", False)
    data["max_depth"] = value

    with pytest.raises(ConfigError, match="max_depth"):
        load_config(write_config(tmp_path, data))