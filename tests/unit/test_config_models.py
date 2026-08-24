from pathlib import Path

from local_llm_lab.config.models import load_model_configs


def test_load_model_configs_lee_toml_real() -> None:
    project_root = Path(__file__).parent.parent.parent
    configs = load_model_configs(project_root=project_root)

    assert "qwen3-4b" in configs
    assert configs["qwen3-4b"].n_ctx == 8192
    assert configs["qwen3-4b"].license == "Apache-2.0"
    assert configs["qwen3-4b"].path == project_root / "models/Qwen3-4B-Q4_K_M.gguf"


def test_load_model_configs_usa_defaults_de_threads_y_gpu_layers(
    tmp_path: Path,
) -> None:
    toml_content = """
[models.custom]
path = "models/custom.gguf"
n_ctx = 2048
"""
    config_file = tmp_path / "models.toml"
    config_file.write_text(toml_content, encoding="utf-8")

    configs = load_model_configs(config_path=config_file, project_root=tmp_path)

    assert configs["custom"].n_threads == 8
    assert configs["custom"].n_gpu_layers == 0
    assert configs["custom"].license == "unknown"
