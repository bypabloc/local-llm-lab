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


def test_load_model_configs_lee_hf_repo_y_hf_file(tmp_path: Path) -> None:
    config_path = tmp_path / "models.toml"
    config_path.write_text(
        '[models.dl]\npath = "models/dl.gguf"\nn_ctx = 1024\n'
        'hf_repo = "org/repo-GGUF"\nhf_file = "dl-Q4_K_M.gguf"\n',
        encoding="utf-8",
    )

    configs = load_model_configs(config_path=config_path, project_root=tmp_path)

    assert configs["dl"].hf_repo == "org/repo-GGUF"
    assert configs["dl"].hf_file == "dl-Q4_K_M.gguf"


def test_load_model_configs_hf_repo_y_hf_file_default_none_si_faltan(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "models.toml"
    config_path.write_text(
        '[models.min]\npath = "models/min.gguf"\nn_ctx = 1024\n', encoding="utf-8"
    )

    configs = load_model_configs(config_path=config_path, project_root=tmp_path)

    assert configs["min"].hf_repo is None
    assert configs["min"].hf_file is None


def test_models_toml_real_path_coincide_con_hf_file() -> None:
    """Si divergen, is_downloaded nunca detecta un modelo ya descargado vía
    hf_hub_download (guarda el archivo con el nombre de hf_file)."""
    configs = load_model_configs()

    for config in configs.values():
        if config.hf_file is not None:
            assert config.path.name == config.hf_file, (
                f"{config.name}: path={config.path.name!r} != "
                f"hf_file={config.hf_file!r}"
            )
