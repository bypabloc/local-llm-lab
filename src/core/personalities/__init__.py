import os
from dataclasses import dataclass
from importlib import resources

DEFAULT_AGENT = "gemma"
_AGENT_ENV_VAR = "LLM_LAB_AGENT"
_PACKAGE = "core.personalities"

_BANNER_PREFIXES = {
    "jarvis": "J.A.R.V.I.S. — ",
    "tars": "TARS — ",
    "gemma": "",
}


class UnknownAgentError(ValueError):
    def __init__(self, name: str) -> None:
        options = ", ".join(sorted(_BANNER_PREFIXES))
        super().__init__(f"agente desconocido '{name}', opciones: {options}")


@dataclass(frozen=True, slots=True)
class Persona:
    name: str
    system_prefix: str
    banner_prefix: str


def _load_system_prefix(name: str) -> str:
    resource = resources.files(_PACKAGE).joinpath(f"{name}.md")
    return resource.read_text(encoding="utf-8").strip()


def get_persona(name: str) -> Persona:
    key = name.strip().lower()
    banner_prefix = _BANNER_PREFIXES.get(key)
    if banner_prefix is None:
        raise UnknownAgentError(name)
    return Persona(
        name=key, system_prefix=_load_system_prefix(key), banner_prefix=banner_prefix
    )


def resolve_agent_name(cli_value: str | None) -> str:
    if cli_value is not None:
        return cli_value
    return os.environ.get(_AGENT_ENV_VAR, DEFAULT_AGENT)


def wrap_banner(persona: Persona, text: str) -> str:
    return f"{persona.banner_prefix}{text}"
