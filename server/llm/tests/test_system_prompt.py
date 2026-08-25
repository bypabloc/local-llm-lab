from core.config.tools import load_tool_prompt
from core.personalities import Persona
from llm.services.system_prompt import build_system_prompt

_TOOLS_HEADER = "\n\nAvailable tools (use the exact line format when it applies):\n"

_BASE_TOOLS = [
    "IP: — current public IP",
    "LOCATION: — approximate current location (city/country)",
    "WEATHER: — current weather",
    "REMEMBER: <fact> — save something about the user to recall it later",
]


def _persona(system_prefix: str = "") -> Persona:
    return Persona(name="gemma", system_prefix=system_prefix, banner_prefix="")


def test_sin_system_file_ni_prefix_ni_tools_extra() -> None:
    result = build_system_prompt(
        _persona(), system_file_content="", allow_shell=False, allow_search=False
    )

    expected = (
        _TOOLS_HEADER
        + "\n".join(f"- {t}" for t in _BASE_TOOLS)
        + load_tool_prompt("weather")
        + load_tool_prompt("memory")
    )
    assert result == expected


def test_con_system_file_y_persona_con_prefix() -> None:
    persona = _persona(system_prefix="Sos J.A.R.V.I.S.")

    result = build_system_prompt(
        persona,
        system_file_content="Sos un asistente útil.",
        allow_shell=False,
        allow_search=False,
    )

    assert result.startswith("Sos J.A.R.V.I.S.\n\nSos un asistente útil.")


def test_persona_sin_prefix_y_con_system_file_no_antepone_separador() -> None:
    result = build_system_prompt(
        _persona(system_prefix=""),
        system_file_content="Instrucciones del archivo.",
        allow_shell=False,
        allow_search=False,
    )

    assert result.startswith("Instrucciones del archivo.")


def test_allow_shell_agrega_run_al_listado_y_al_prompt_de_tool() -> None:
    result = build_system_prompt(
        _persona(), system_file_content="", allow_shell=True, allow_search=False
    )

    assert "RUN: <command> — run a shell command" in result
    assert load_tool_prompt("shell") in result
    assert "SEARCH:" not in result


def test_allow_search_agrega_search_al_listado_y_al_prompt_de_tool() -> None:
    result = build_system_prompt(
        _persona(), system_file_content="", allow_shell=False, allow_search=True
    )

    assert "SEARCH: <query> — search the internet" in result
    assert load_tool_prompt("search") in result
    assert "RUN:" not in result


def test_orden_de_bloques_es_weather_memory_shell_search() -> None:
    result = build_system_prompt(
        _persona(), system_file_content="", allow_shell=True, allow_search=True
    )

    weather_idx = result.index(load_tool_prompt("weather"))
    memory_idx = result.index(load_tool_prompt("memory"))
    shell_idx = result.index(load_tool_prompt("shell"))
    search_idx = result.index(load_tool_prompt("search"))

    assert weather_idx < memory_idx < shell_idx < search_idx
