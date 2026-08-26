import pytest

from llm.personalities import (
    DEFAULT_AGENT,
    UnknownAgentError,
    get_persona,
    resolve_agent_name,
    wrap_banner,
)


@pytest.mark.parametrize("name", ["jarvis", "tars", "gemma"])
def test_get_persona_carga_cada_persona_existente(name: str) -> None:
    persona = get_persona(name)

    assert persona.name == name


@pytest.mark.parametrize("name", ["jarvis", "tars"])
def test_get_persona_con_prefijo_tiene_system_prefix_no_vacio(name: str) -> None:
    assert get_persona(name).system_prefix


def test_get_persona_lanza_unknown_agent_error_si_no_existe() -> None:
    with pytest.raises(UnknownAgentError):
        get_persona("no-existe")


def test_get_persona_es_case_insensitive() -> None:
    assert get_persona("JARVIS").name == "jarvis"


def test_resolve_agent_name_usa_valor_explicito_si_se_pasa() -> None:
    assert resolve_agent_name("tars") == "tars"


def test_resolve_agent_name_usa_env_var_si_no_hay_valor_explicito(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_LAB_AGENT", "jarvis")

    assert resolve_agent_name(None) == "jarvis"


def test_resolve_agent_name_usa_default_sin_valor_ni_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_LAB_AGENT", raising=False)

    assert resolve_agent_name(None) == DEFAULT_AGENT


def test_wrap_banner_antepone_prefijo_de_persona() -> None:
    persona = get_persona("jarvis")

    assert wrap_banner(persona, "hola").startswith("J.A.R.V.I.S. — ")


def test_wrap_banner_gemma_no_agrega_prefijo() -> None:
    persona = get_persona("gemma")

    assert wrap_banner(persona, "hola") == "hola"
