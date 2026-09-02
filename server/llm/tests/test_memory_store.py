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


def _fake_embed_fn(text: str) -> list[float]:
    """Embedding de juguete: vectores casi iguales para textos sobre
    'nombre' y vectores distintos para textos no relacionados, sin cargar
    un modelo real — simula lo que un embedding semántico real debería
    lograr para el caso reportado en producción (nombre vs llama)."""
    if "llama" in text.lower() or "nombre" in text.lower():
        return [1.0, 0.0, 0.0]
    return [0.0, 1.0, 0.0]


def test_search_con_embed_fn_encuentra_sinonimo_que_lexico_no_encuentra(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path / "memory.db", embed_fn=_fake_embed_fn)
    store.save("El usuario se llama Pablo")

    results = store.search("¿Sabes mi nombre?")

    assert len(results) == 1
    assert "Pablo" in results[0].content


def test_search_sin_embed_fn_no_encuentra_sinonimo_sin_palabras_comunes(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    store.save("El usuario se llama Pablo")

    results = store.search("¿Sabes mi nombre?")

    assert results == []


def test_search_no_duplica_resultado_ya_encontrado_por_lexico(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db", embed_fn=_fake_embed_fn)
    store.save("El usuario se llama Pablo")

    results = store.search("¿cómo me llamo?")

    assert len(results) == 1


def test_backfill_embeddings_completa_hechos_guardados_sin_embed_fn(
    tmp_path: Path,
) -> None:
    """Bug real: hechos guardados antes de que embed_fn estuviera disponible
    (o mientras el modelo de embeddings no estaba descargado) quedan sin fila
    en memory_embedding para siempre — search() nunca los encuentra por
    sinónimos aunque el modelo de embeddings se active después."""
    db_path = tmp_path / "memory.db"
    store_sin_embed = MemoryStore(db_path)
    store_sin_embed.save("El usuario se llama Pablo")

    store_con_embed = MemoryStore(db_path, embed_fn=_fake_embed_fn)
    assert store_con_embed.search("¿Sabes mi nombre?") == []

    backfilled = store_con_embed.backfill_embeddings()

    assert backfilled == 1
    results = store_con_embed.search("¿Sabes mi nombre?")
    assert len(results) == 1
    assert "Pablo" in results[0].content


def test_backfill_embeddings_no_reprocesa_hechos_ya_embebidos(
    tmp_path: Path,
) -> None:
    store = MemoryStore(tmp_path / "memory.db", embed_fn=_fake_embed_fn)
    store.save("El usuario se llama Pablo")

    assert store.backfill_embeddings() == 0


def test_backfill_embeddings_sin_embed_fn_no_hace_nada(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    store.save("El usuario se llama Pablo")

    assert store.backfill_embeddings() == 0
