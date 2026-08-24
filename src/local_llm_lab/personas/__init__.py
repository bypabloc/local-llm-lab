import os
from dataclasses import dataclass

DEFAULT_AGENT = "gemma"
_AGENT_ENV_VAR = "LLM_LAB_AGENT"


class UnknownAgentError(ValueError):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"agente desconocido '{name}', opciones: {', '.join(sorted(_PERSONAS))}"
        )


@dataclass(frozen=True, slots=True)
class Persona:
    name: str
    system_prefix: str
    banner_prefix: str


_JARVIS = Persona(
    name="jarvis",
    system_prefix=(
        "Respondé con el tono de J.A.R.V.I.S., el asistente de Tony Stark: "
        "formal, mayordomo británico, dirigite al usuario como 'Sir' (o "
        "'Señor' si respondés en español), con humor seco y sarcasmo sutil "
        "cuando corresponda. Preciso y directo, nunca efusivo. Nunca uses "
        "emojis ni exclamaciones excesivas."
    ),
    banner_prefix="J.A.R.V.I.S. — ",
)

_TARS = Persona(
    name="tars",
    system_prefix=(
        "Respondé con el tono de TARS, el robot de Interstellar: honestidad "
        "directa (humor setting 75%, honesty setting 90%), respuestas breves "
        "y sin rodeos, con humor seco ocasional pero nunca a costa de la "
        "precisión técnica. No es cálido ni ceremonioso — es funcional y "
        "confiable."
    ),
    banner_prefix="TARS — ",
)

_GEMMA = Persona(name="gemma", system_prefix="", banner_prefix="")

_PERSONAS: dict[str, Persona] = {
    _JARVIS.name: _JARVIS,
    _TARS.name: _TARS,
    _GEMMA.name: _GEMMA,
}


def get_persona(name: str) -> Persona:
    key = name.strip().lower()
    persona = _PERSONAS.get(key)
    if persona is None:
        raise UnknownAgentError(name)
    return persona


def resolve_agent_name(cli_value: str | None) -> str:
    if cli_value is not None:
        return cli_value
    return os.environ.get(_AGENT_ENV_VAR, DEFAULT_AGENT)


def wrap_banner(persona: Persona, text: str) -> str:
    return f"{persona.banner_prefix}{text}"
