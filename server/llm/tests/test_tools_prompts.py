import pytest

from llm.config.tools import load_tool_prompt


@pytest.mark.parametrize("name", ["memory", "search", "shell", "weather"])
def test_load_tool_prompt_carga_cada_tool_existente(name: str) -> None:
    prompt = load_tool_prompt(name)

    assert prompt.startswith("\n\n")
    assert prompt.strip()


def test_load_tool_prompt_lanza_file_not_found_si_no_existe() -> None:
    with pytest.raises(FileNotFoundError):
        load_tool_prompt("no-existe")
