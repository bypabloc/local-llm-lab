from pathlib import Path

from llm.memory.store import MemoryStore


def test_save_y_search_encuentra_hecho_guardado(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")

    store.save("el usuario se llama Pablo y prefiere respuestas concisas")
    results = store.search("Pablo")

    assert len(results) == 1
    assert "Pablo" in results[0].content


def test_search_encuentra_hecho_con_pregunta_que_no_comparte_palabras_clave(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    store.save("el usuario se llama Pablo")

    results = store.search("¿cómo me llamo?")

    assert len(results) == 1


def test_save_deduplica_contenido_normalizado(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")

    store.save("El usuario se llama Pablo")
    store.save("el   usuario se llama pablo")

    assert len(store.search("Pablo")) == 1


def test_search_sin_resultados_devuelve_lista_vacia(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")

    assert store.search("cualquier cosa") == []


def test_search_respeta_limit(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    for i in range(5):
        store.save(f"hecho numero {i} sobre gatos")

    results = store.search("gatos", limit=2)

    assert len(results) == 2
