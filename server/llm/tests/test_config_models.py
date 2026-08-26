from pathlib import Path

from llm.config.models import ModelConfig, load_model_configs

_TOML_CONTENT = """
[models.test-model]
path = "models/test.gguf"
n_ctx = 2048
n_threads = 4
n_gpu_layers = 0
license = "MIT"
"""


def test_load_model_configs_resuelve_path_relativo_a_project_root(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "models.toml"
    config_path.write_text(_TOML_CONTENT, encoding="utf-8")

    configs = load_model_configs(config_path=config_path, project_root=tmp_path)

    assert configs["test-model"] == ModelConfig(
        name="test-model",
        path=tmp_path / "models/test.gguf",
        n_ctx=2048,
        n_threads=4,
        n_gpu_layers=0,
        license="MIT",
    )


def test_load_model_configs_usa_defaults_si_faltan_opcionales(tmp_path: Path) -> None:
    config_path = tmp_path / "models.toml"
    config_path.write_text(
        '[models.min]\npath = "models/min.gguf"\nn_ctx = 1024\n', encoding="utf-8"
    )

    configs = load_model_configs(config_path=config_path, project_root=tmp_path)

    assert configs["min"].n_threads == 8
    assert configs["min"].n_gpu_layers == 0
    assert configs["min"].license == "unknown"


def test_load_model_configs_con_models_dir_usa_solo_el_filename_de_la_entrada(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "models.toml"
    config_path.write_text(_TOML_CONTENT, encoding="utf-8")
    custom_dir = tmp_path / "custom"

    configs = load_model_configs(
        config_path=config_path, project_root=tmp_path, models_dir=custom_dir
    )

    assert configs["test-model"].path == custom_dir / "test.gguf"


def test_load_model_configs_repo_real_resuelve_project_root_correcto() -> None:
    configs = load_model_configs()

    assert configs
    for config in configs.values():
        assert config.path.parts[-2] == "models"
