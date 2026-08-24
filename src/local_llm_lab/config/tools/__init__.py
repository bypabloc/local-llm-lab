from importlib import resources

_PACKAGE = "local_llm_lab.config.tools"


def load_tool_prompt(name: str) -> str:
    """Carga el system prompt de la tool `name` desde `config/tools/<name>.md`.

    El texto se antepone con un separador de párrafo (`\\n\\n`) para
    concatenarse directamente al system prompt existente.
    """
    resource = resources.files(_PACKAGE).joinpath(f"{name}.md")
    if not resource.is_file():
        raise FileNotFoundError(f"no existe el prompt de tool '{name}'")
    return "\n\n" + resource.read_text(encoding="utf-8").strip()
