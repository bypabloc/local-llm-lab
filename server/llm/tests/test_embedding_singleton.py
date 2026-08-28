from pathlib import Path

from llm.services import embedding_singleton
from llm.services.embedding_singleton import get_embed_fn


def test_get_embed_fn_devuelve_none_si_modelo_no_descargado(tmp_path: Path) -> None:
    embedding_singleton.reset()

    embed_fn = get_embed_fn(tmp_path)

    assert embed_fn is None


def test_get_embed_fn_cachea_el_fallo_sin_reintentar_carga(tmp_path: Path) -> None:
    embedding_singleton.reset()

    get_embed_fn(tmp_path)
    assert embedding_singleton._load_failed is True

    # segunda llamada no debería reintentar cargar (short-circuit)
    embed_fn = get_embed_fn(tmp_path)
    assert embed_fn is None
