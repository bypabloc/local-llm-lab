from llm.memory.marker import extract_remember_note


def test_extract_remember_note_devuelve_ultimo_hecho_marcado() -> None:
    text = "hola\nREMEMBER: al usuario le gusta el café\nfin"

    assert extract_remember_note(text) == "al usuario le gusta el café"


def test_extract_remember_note_devuelve_none_sin_marcador() -> None:
    assert extract_remember_note("respuesta sin hecho") is None


def test_extract_remember_note_ignora_marcador_vacio() -> None:
    assert extract_remember_note("REMEMBER:   \n") is None
