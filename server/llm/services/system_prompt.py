from llm.config.tools import load_tool_prompt
from llm.personalities import Persona

_TOOLS_HEADER = "\n\nAvailable tools (use the exact line format when it applies):\n"

_BASE_TOOLS = [
    "IP: — current public IP",
    "LOCATION: — approximate current location (city/country)",
    "WEATHER: — current weather",
    "REMEMBER: <fact> — save something about the user to recall it later",
]


def _apply_persona(persona: Persona, system: str) -> str:
    if not persona.system_prefix:
        return system
    return f"{persona.system_prefix}\n\n{system}" if system else persona.system_prefix


def build_system_prompt(
    persona: Persona,
    system_file_content: str,
    allow_shell: bool,
    allow_search: bool,
) -> str:
    """Arma el system prompt igual que `_run_interactive` en core/cli/main.py.

    Orden fijo: persona -> system_file -> tools header -> weather -> memory
    -> shell (si allow_shell) -> search (si allow_search).
    """
    system = _apply_persona(persona, system_file_content)

    tool_names = list(_BASE_TOOLS)
    if allow_shell:
        tool_names.append("RUN: <command> — run a shell command")
    if allow_search:
        tool_names.append("SEARCH: <query> — search the internet")

    system += _TOOLS_HEADER + "\n".join(f"- {t}" for t in tool_names)
    system += load_tool_prompt("weather")
    system += load_tool_prompt("memory")
    if allow_shell:
        system += load_tool_prompt("shell")
    if allow_search:
        system += load_tool_prompt("search")

    return system
