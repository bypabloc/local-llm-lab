import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from llm.backends.protocol import ChatMessage, LLMBackend
from llm.memory import MemoryStore, extract_remember_note
from llm.shell.location import (
    extract_ip_query,
    extract_location_query,
    extract_weather_query,
    get_location,
    get_public_ip,
    get_weather_for_current_location,
)
from llm.shell.runner import extract_run_command
from llm.shell.web_search import extract_search_query, search_web

logger = logging.getLogger(__name__)

ChatEventKind = Literal["token", "run_proposed", "tool_result", "assistant_done"]


@dataclass(frozen=True, slots=True)
class ChatEvent:
    kind: ChatEventKind
    payload: dict[str, Any]


def _recall_relevant_memories(user_input: str, store: MemoryStore) -> str | None:
    logger.debug("_recall_relevant_memories: buscando en memoria")
    try:
        entries = store.search(user_input, limit=3)
    except Exception:
        logger.exception("_recall_relevant_memories: fallo buscando en memoria")
        raise
    if not entries:
        return None
    formatted = "\n".join(f"- {entry.content}" for entry in entries)
    return f"[you already know this about the user:\n{formatted}]"


def _handle_search_query(response_text: str) -> str | None:
    query = extract_search_query(response_text)
    if query is None:
        return None
    outcome = search_web(query)
    if outcome.error is not None:
        return f"[búsqueda '{query}' falló: {outcome.error}]"
    if not outcome.results:
        return f"[búsqueda '{query}' no encontró resultados]"
    formatted = "\n".join(
        f"- {r.title} ({r.url}): {r.snippet}" for r in outcome.results
    )
    return f"[resultados de búsqueda para '{query}':\n{formatted}]"


def _handle_ip_query(response_text: str) -> str | None:
    if not extract_ip_query(response_text):
        return None
    outcome = get_public_ip()
    if outcome.error is not None:
        return f"[consulta de IP falló: {outcome.error}]"
    return f"[IP pública actual: {outcome.ip}]"


def _handle_location_query(response_text: str) -> str | None:
    if not extract_location_query(response_text):
        return None
    outcome = get_location()
    if outcome.error is not None:
        return f"[consulta de ubicación falló: {outcome.error}]"
    return f"[ubicación aproximada actual: {outcome.city}, {outcome.country}]"


def _handle_weather_query(response_text: str) -> str | None:
    if not extract_weather_query(response_text):
        return None
    outcome = get_weather_for_current_location()
    if outcome.error is not None:
        return f"[consulta de clima falló: {outcome.error}]"
    return (
        f"[clima actual en {outcome.city}, {outcome.country}: "
        f"{outcome.temperature_celsius}°C, código de clima {outcome.weather_code}]"
    )


def _handle_remember_note(response_text: str, store: MemoryStore) -> str | None:
    note = extract_remember_note(response_text)
    if note is None:
        return None
    try:
        store.save(note)
    except Exception:
        logger.exception("_handle_remember_note: fallo guardando nota en memoria")
        raise
    return f"[guardado en memoria: {note}]"


def _stream(
    backend: LLMBackend,
    history: list[ChatMessage],
    max_tokens: int,
    no_think: bool,
) -> Iterator[ChatEvent]:
    if no_think and history and history[-1]["role"] == "user":
        history[-1] = {
            "role": "user",
            "content": f"{history[-1]['content']} /no_think",
        }

    logger.debug("_stream: iniciando stream_chat, %d mensajes", len(history))
    chunks: list[str] = []
    try:
        for token in backend.stream_chat(history, max_tokens=max_tokens):
            chunks.append(token)
            yield ChatEvent("token", {"text": token})
    except Exception:
        logger.exception("_stream: fallo durante backend.stream_chat")
        raise

    response_text = "".join(chunks)
    logger.debug("_stream: fin, %d chars generados", len(response_text))
    history.append({"role": "assistant", "content": response_text})


def run_chat_turn(
    backend: LLMBackend,
    history: list[ChatMessage],
    memory_store: MemoryStore,
    max_tokens: int,
    no_think: bool,
    allow_shell: bool,
    allow_search: bool,
) -> Iterator[ChatEvent]:
    """Orquesta un turno de chat, réplica de `_run_interactive` (core/cli/main.py).

    Muta `history` in-place igual que el CLI. Si aparece RUN:, corta el turno
    con `run_proposed` sin evaluar el resto de marcadores ni hacer la ronda
    de seguimiento — la confirmación llega en una request HTTP aparte.
    """
    logger.info(
        "run_chat_turn: inicio, %d mensajes, allow_shell=%s allow_search=%s",
        len(history),
        allow_shell,
        allow_search,
    )
    if history and history[-1]["role"] == "user":
        recalled = _recall_relevant_memories(history[-1]["content"], memory_store)
        if recalled is not None:
            logger.debug("run_chat_turn: memoria recuperada, inyectando en history")
            history.insert(len(history) - 1, {"role": "system", "content": recalled})

    logger.debug("run_chat_turn: primer _stream")
    yield from _stream(backend, history, max_tokens, no_think)
    response_text = history[-1]["content"]

    if allow_shell:
        command = extract_run_command(response_text)
        if command is not None:
            logger.info("run_chat_turn: RUN: detectado, cortando turno")
            yield ChatEvent("run_proposed", {"command": command})
            return

    tool_result: str | None = None
    if allow_search:
        tool_result = _handle_search_query(response_text)
    if tool_result is None:
        tool_result = _handle_ip_query(response_text)
    if tool_result is None:
        tool_result = _handle_location_query(response_text)
    if tool_result is None:
        tool_result = _handle_weather_query(response_text)
    if tool_result is None:
        tool_result = _handle_remember_note(response_text, memory_store)

    if tool_result is None:
        logger.debug("run_chat_turn: sin marcador de tool, fin de turno")
        yield ChatEvent("assistant_done", {})
        return

    logger.info("run_chat_turn: tool_result detectado, ronda de seguimiento")
    # ponytail: role "user" y no "system" — algunos templates de chat (Gemma)
    # exigen alternancia estricta user/assistant/user/assistant y rechazan un
    # "system" intercalado a mitad de conversación (ValueError de llama-cpp).
    history.append({"role": "user", "content": tool_result})
    yield ChatEvent("tool_result", {"text": tool_result})

    yield from _stream(backend, history, max_tokens, no_think)
    yield ChatEvent("assistant_done", {})
