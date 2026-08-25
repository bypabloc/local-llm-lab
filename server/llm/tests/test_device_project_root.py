from pathlib import Path

import pytest

from llm.services.device import resolve_project_root


def test_resolve_project_root_usa_env_var_si_esta_seteada(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LLM_LAB_PROJECT_ROOT", str(tmp_path))

    assert resolve_project_root() == tmp_path


def test_resolve_project_root_usa_default_si_no_hay_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_LAB_PROJECT_ROOT", raising=False)

    assert resolve_project_root() is None
