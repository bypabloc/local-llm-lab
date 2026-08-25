from core.memory.marker import extract_remember_note


def test_extract_remember_note_encuentra_el_marcador() -> None:
    text = "Entendido.\nREMEMBER: al usuario le gusta que le escriban conciso"

    note = extract_remember_note(text)

    assert note == "al usuario le gusta que le escriban conciso"


def test_extract_remember_note_sin_marcador_devuelve_none() -> None:
    assert extract_remember_note("una respuesta normal sin marcador") is None


def test_extract_remember_note_usa_la_ultima_coincidencia() -> None:
    text = "REMEMBER: primera nota\nsigo pensando\nREMEMBER: segunda nota"

    note = extract_remember_note(text)

    assert note == "segunda nota"


def test_extract_remember_note_vacio_devuelve_none() -> None:
    assert extract_remember_note("REMEMBER:   \n") is None
