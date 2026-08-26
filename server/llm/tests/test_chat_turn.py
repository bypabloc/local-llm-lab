from pathlib import Path

import pytest

from llm.memory.store import MemoryStore
from llm.services.chat_turn import ChatEvent, run_chat_turn
from llm.tests.fakes import FakeBackend, make_model_config


@pytest.fixture
def memory_store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory.db")


def _events(
    backend: FakeBackend,
    history: list[dict[str, str]],
    memory_store: MemoryStore,
    allow_shell: bool = False,
    allow_search: bool = False,
) -> list[ChatEvent]:
    return list(
        run_chat_turn(
            backend,
            history,  # type: ignore[arg-type]
            memory_store,
            max_tokens=1024,
            no_think=False,
            allow_shell=allow_shell,
            allow_search=allow_search,
        )
    )


def test_turno_sin_tools_emite_tokens_y_termina_con_assistant_done(
    memory_store: MemoryStore,
) -> None:
    backend = FakeBackend(make_model_config(), reply="hola")
    history: list[dict[str, str]] = [{"role": "user", "content": "hola"}]

    events = _events(backend, history, memory_store)

    tokens = [e for e in events if e.kind == "token"]
    assert "".join(e.payload["text"] for e in tokens) == "hola"
    assert events[-1].kind == "assistant_done"
    assert history[-1] == {"role": "assistant", "content": "hola"}


def test_recall_de_memoria_inyecta_mensaje_system_antes_del_turno(
    memory_store: MemoryStore,
) -> None:
    memory_store.save("el usuario se llama Pablo")
    backend = FakeBackend(make_model_config(), reply="ok")
    history: list[dict[str, str]] = [{"role": "user", "content": "como me llamo"}]

    _events(backend, history, memory_store)

    system_messages = [m for m in history if m["role"] == "system"]
    assert any("Pablo" in m["content"] for m in system_messages)


def test_no_think_agrega_sufijo_al_ultimo_mensaje_user_antes_de_stream(
    memory_store: MemoryStore,
) -> None:
    backend = FakeBackend(make_model_config(), reply="ok")
    history: list[dict[str, str]] = [{"role": "user", "content": "hola"}]

    list(
        run_chat_turn(
            backend,
            history,  # type: ignore[arg-type]
            memory_store,
            max_tokens=1024,
            no_think=True,
            allow_shell=False,
            allow_search=False,
        )
    )

    last_call_messages = backend.stream_calls[0]
    assert last_call_messages[-1]["content"].endswith(" /no_think")


def test_run_detectado_corta_el_turno_sin_ronda_de_seguimiento(
    memory_store: MemoryStore,
) -> None:
    backend = FakeBackend(make_model_config(), reply="RUN: ls -la")
    history: list[dict[str, str]] = [{"role": "user", "content": "listá archivos"}]

    events = _events(backend, history, memory_store, allow_shell=True)

    assert events[-1].kind == "run_proposed"
    assert events[-1].payload["command"] == "ls -la"
    assert len(backend.stream_calls) == 1


def test_run_sin_allow_shell_no_se_detecta(memory_store: MemoryStore) -> None:
    backend = FakeBackend(make_model_config(), reply="RUN: ls -la")
    history: list[dict[str, str]] = [{"role": "user", "content": "hola"}]

    events = _events(backend, history, memory_store, allow_shell=False)

    assert not any(e.kind == "run_proposed" for e in events)
    assert events[-1].kind == "assistant_done"


def test_search_detectado_dispara_ronda_de_seguimiento_unica(
    monkeypatch: pytest.MonkeyPatch, memory_store: MemoryStore
) -> None:
    from llm.shell.web_search import SearchOutcome, SearchResult

    def fake_search_web(query: str, **kwargs: object) -> SearchOutcome:
        return SearchOutcome(
            query=query,
            results=[SearchResult(title="t", url="u", snippet="s")],
        )

    monkeypatch.setattr("llm.services.chat_turn.search_web", fake_search_web)

    backend = FakeBackend(make_model_config(), reply="SEARCH: clima santiago")
    history: list[dict[str, str]] = [{"role": "user", "content": "buscá algo"}]

    events = _events(backend, history, memory_store, allow_search=True)

    assert any(e.kind == "tool_result" for e in events)
    assert events[-1].kind == "assistant_done"
    assert len(backend.stream_calls) == 2


def test_remember_detectado_guarda_en_memoria_y_hace_seguimiento(
    memory_store: MemoryStore,
) -> None:
    backend = FakeBackend(make_model_config(), reply="REMEMBER: le gusta el café")
    history: list[dict[str, str]] = [{"role": "user", "content": "recordá algo"}]

    events = _events(backend, history, memory_store)

    assert any(e.kind == "tool_result" for e in events)
    assert len(backend.stream_calls) == 2
    assert memory_store.search("café")


def test_ip_detectado_dispara_ronda_de_seguimiento(
    monkeypatch: pytest.MonkeyPatch, memory_store: MemoryStore
) -> None:
    from llm.shell.location import IpOutcome

    monkeypatch.setattr(
        "llm.services.chat_turn.get_public_ip",
        lambda: IpOutcome(ip="1.2.3.4"),
    )

    backend = FakeBackend(make_model_config(), reply="IP:")
    history: list[dict[str, str]] = [{"role": "user", "content": "cuál es mi ip"}]

    events = _events(backend, history, memory_store)

    tool_events = [e for e in events if e.kind == "tool_result"]
    assert len(tool_events) == 1
    assert "1.2.3.4" in tool_events[0].payload["text"]
    assert len(backend.stream_calls) == 2


def test_location_detectado_dispara_ronda_de_seguimiento(
    monkeypatch: pytest.MonkeyPatch, memory_store: MemoryStore
) -> None:
    from llm.shell.location import LocationOutcome

    monkeypatch.setattr(
        "llm.services.chat_turn.get_location",
        lambda: LocationOutcome(
            city="Lima", country="Peru", latitude=-12.0, longitude=-77.0
        ),
    )

    backend = FakeBackend(make_model_config(), reply="LOCATION:")
    history: list[dict[str, str]] = [{"role": "user", "content": "dónde estoy"}]

    events = _events(backend, history, memory_store)

    tool_events = [e for e in events if e.kind == "tool_result"]
    assert len(tool_events) == 1
    assert "Lima" in tool_events[0].payload["text"]


def test_weather_detectado_dispara_ronda_de_seguimiento(
    monkeypatch: pytest.MonkeyPatch, memory_store: MemoryStore
) -> None:
    from llm.shell.location import WeatherForLocationOutcome

    monkeypatch.setattr(
        "llm.services.chat_turn.get_weather_for_current_location",
        lambda: WeatherForLocationOutcome(
            city="Lima", country="Peru", temperature_celsius=18.0, weather_code=3
        ),
    )

    backend = FakeBackend(make_model_config(), reply="WEATHER:")
    history: list[dict[str, str]] = [{"role": "user", "content": "qué clima hace"}]

    events = _events(backend, history, memory_store)

    tool_events = [e for e in events if e.kind == "tool_result"]
    assert len(tool_events) == 1
    assert "18.0" in tool_events[0].payload["text"]


def test_orden_de_deteccion_ip_antes_que_location_antes_que_weather(
    monkeypatch: pytest.MonkeyPatch, memory_store: MemoryStore
) -> None:
    from llm.shell.location import IpOutcome

    monkeypatch.setattr(
        "llm.services.chat_turn.get_public_ip", lambda: IpOutcome(ip="9.9.9.9")
    )

    backend = FakeBackend(make_model_config(), reply="IP:\nLOCATION:\nWEATHER:")
    history: list[dict[str, str]] = [{"role": "user", "content": "info"}]

    events = _events(backend, history, memory_store)

    tool_events = [e for e in events if e.kind == "tool_result"]
    assert len(tool_events) == 1
    assert "9.9.9.9" in tool_events[0].payload["text"]


def test_orden_de_deteccion_run_antes_que_search(memory_store: MemoryStore) -> None:
    backend = FakeBackend(make_model_config(), reply="RUN: ls\nSEARCH: algo")
    history: list[dict[str, str]] = [{"role": "user", "content": "hola"}]

    events = _events(
        backend, history, memory_store, allow_shell=True, allow_search=True
    )

    assert events[-1].kind == "run_proposed"
