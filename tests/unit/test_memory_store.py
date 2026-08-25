from pathlib import Path

import pytest

from core.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory.db")


def test_save_y_search_encuentra_por_palabra_clave(store: MemoryStore) -> None:
    store.save("al usuario le gusta que le respondan de forma concisa")

    results = store.search("concisa")

    assert len(results) == 1
    assert "concisa" in results[0].content


def test_search_respeta_el_limite(store: MemoryStore) -> None:
    for i in range(5):
        store.save(f"nota número {i} sobre preferencias del usuario")

    results = store.search("preferencias", limit=2)

    assert len(results) == 2


def test_search_ordena_por_relevancia_mas_reciente_primero_en_empate(
    store: MemoryStore,
) -> None:
    store.save("el usuario es ingeniero de software")
    store.save("el usuario es ingeniero de datos")

    results = store.search("ingeniero")

    assert len(results) == 2
    assert results[0].content == "el usuario es ingeniero de datos"


def test_save_persiste_entre_instancias_del_store(tmp_path: Path) -> None:
    db_path = tmp_path / "memory.db"
    MemoryStore(db_path).save("el usuario se llama Pablo")

    results = MemoryStore(db_path).search("Pablo")

    assert len(results) == 1


def test_save_crea_el_directorio_padre_si_no_existe(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "dir" / "memory.db"

    MemoryStore(db_path).save("nota de prueba")

    assert db_path.exists()


def test_search_encuentra_hecho_con_pregunta_que_no_comparte_palabras_clave(
    store: MemoryStore,
) -> None:
    """Caso real: el usuario pregunta '¿cómo me llamo?' sin usar la palabra
    'llama' ni 'nombre' tal cual aparece en el hecho guardado. Con AND
    estricto esto no matchea nada — necesita OR + filtrado de stopwords
    para no perder el hecho por diferencias de redacción."""
    store.save("el usuario se llama Pablo y prefiere respuestas concisas")

    results = store.search("como me llamo")

    assert len(results) == 1


def test_search_ignora_stopwords_para_no_traer_resultados_irrelevantes(
    store: MemoryStore,
) -> None:
    store.save("el usuario prefiere respuestas en español")

    results = store.search("clima en Santiago")

    assert results == []


def test_save_no_duplica_un_hecho_identico(store: MemoryStore) -> None:
    store.save("el usuario se llama Pablo")
    store.save("el usuario se llama Pablo")

    results = store.search("Pablo")

    assert len(results) == 1


def test_save_no_duplica_ignorando_mayusculas_y_espacios(store: MemoryStore) -> None:
    store.save("El usuario se llama Pablo")
    store.save("  el usuario se llama pablo  ")

    results = store.search("Pablo")

    assert len(results) == 1


def test_save_permite_hechos_distintos(store: MemoryStore) -> None:
    store.save("el usuario se llama Pablo")
    store.save("el usuario prefiere respuestas concisas")

    results = store.search("usuario")

    assert len(results) == 2
