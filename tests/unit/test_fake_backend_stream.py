from tests.unit.fakes import FakeBackend, make_model_config


def test_stream_chat_yieldea_texto_en_fragmentos() -> None:
    config = make_model_config("fake")
    backend = FakeBackend(config, reply="una dos tres")

    chunks = list(
        backend.stream_chat(
            [
                {"role": "system", "content": "sos un asistente"},
                {"role": "user", "content": "hola"},
            ],
            max_tokens=64,
        )
    )

    assert "".join(chunks) == "una dos tres"
    assert backend.calls == [("sos un asistente", "hola")]
