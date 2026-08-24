import pytest

from local_llm_lab.personas import (
    DEFAULT_AGENT,
    UnknownAgentError,
    get_persona,
    resolve_agent_name,
    wrap_banner,
)


def test_default_agent_es_gemma() -> None:
    assert DEFAULT_AGENT == "gemma"


def test_get_persona_jarvis_menciona_sir_y_tiene_prefix() -> None:
    persona = get_persona("jarvis")
    assert "Sir" in persona.system_prefix
    assert persona.banner_prefix != ""


def test_get_persona_tars_menciona_humor_setting() -> None:
    persona = get_persona("tars")
    assert "humor" in persona.system_prefix.lower()


def test_get_persona_gemma_es_neutral_sin_prefix() -> None:
    persona = get_persona("gemma")
    assert persona.system_prefix == ""
    assert persona.banner_prefix == ""


def test_get_persona_case_insensitive() -> None:
    assert get_persona("JARVIS").name == "jarvis"


def test_get_persona_agente_desconocido_lanza_error() -> None:
    with pytest.raises(UnknownAgentError):
        get_persona("skynet")


def test_resolve_agent_name_prioriza_flag_sobre_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_LAB_AGENT", "tars")
    assert resolve_agent_name(cli_value="jarvis") == "jarvis"


def test_resolve_agent_name_usa_env_si_no_hay_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_LAB_AGENT", "tars")
    assert resolve_agent_name(cli_value=None) == "tars"


def test_resolve_agent_name_default_gemma_sin_flag_ni_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_LAB_AGENT", raising=False)
    assert resolve_agent_name(cli_value=None) == DEFAULT_AGENT


def test_wrap_banner_antepone_banner_prefix() -> None:
    persona = get_persona("jarvis")
    assert wrap_banner(persona, "listo").startswith(persona.banner_prefix)


def test_wrap_banner_gemma_no_modifica_texto() -> None:
    persona = get_persona("gemma")
    assert wrap_banner(persona, "listo") == "listo"
