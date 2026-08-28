import dataclasses
from pathlib import Path
from unittest.mock import patch

import pytest

from llm.services.model_downloads import MissingHfMetadataError, download_model
from llm.tests.fakes import make_model_config


def test_download_model_lanza_si_falta_hf_repo(tmp_path: Path) -> None:
    config = make_model_config("sin-hf")

    with pytest.raises(MissingHfMetadataError):
        list(download_model(config, tmp_path))


def test_download_model_emite_progreso_y_done(tmp_path: Path) -> None:
    config = dataclasses.replace(
        make_model_config("con-hf"),
        hf_repo="org/repo-GGUF",
        hf_file="con-hf-Q4_K_M.gguf",
    )

    def fake_hf_hub_download(
        *, repo_id: str, filename: str, local_dir: Path, tqdm_class: type
    ) -> str:
        bar = tqdm_class(total=100)
        bar.update(50)
        bar.update(50)
        return str(local_dir / filename)

    with patch("huggingface_hub.hf_hub_download", side_effect=fake_hf_hub_download):
        events = list(download_model(config, tmp_path))

    kinds = [e.kind for e in events]
    assert kinds == ["progress", "progress", "done"]
    assert events[-1].payload == {"model": "con-hf"}
    assert events[0].payload["downloaded"] == 50
    assert events[1].payload["downloaded"] == 100


def test_download_model_emite_error_si_hf_hub_download_falla(tmp_path: Path) -> None:
    config = dataclasses.replace(
        make_model_config("falla"),
        hf_repo="org/repo-GGUF",
        hf_file="falla-Q4_K_M.gguf",
    )

    with patch(
        "huggingface_hub.hf_hub_download", side_effect=RuntimeError("red caída")
    ):
        events = list(download_model(config, tmp_path))

    assert events[-1].kind == "error"
    assert events[-1].payload["model"] == "falla"
