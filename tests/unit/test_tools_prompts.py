import pytest

from local_llm_lab.config.tools import load_tool_prompt


def test_load_tool_prompt_shell_menciona_run() -> None:
    assert "RUN:" in load_tool_prompt("shell")


def test_load_tool_prompt_search_menciona_search() -> None:
    assert "SEARCH:" in load_tool_prompt("search")


def test_load_tool_prompt_weather_menciona_weather() -> None:
    assert "WEATHER:" in load_tool_prompt("weather")


def test_load_tool_prompt_desconocido_lanza_error() -> None:
    with pytest.raises(FileNotFoundError):
        load_tool_prompt("no-existe")
