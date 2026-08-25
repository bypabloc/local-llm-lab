import subprocess
import sys

from local_llm_lab.cli.main import _REPO_ROOT, _ensure_searxng_running


def test_repo_root_apunta_a_la_raiz_del_repo_donde_vive_devtools() -> None:
    """`devtools/` está fuera de src/ — el entry point instalado no lo trae a
    sys.path por sí solo (solo agrega src/ vía el editable install), así que
    _REPO_ROOT debe resolver exactamente al directorio que contiene devtools/."""
    assert (_REPO_ROOT / "devtools" / "searxng" / "main.py").is_file()


def test_ensure_searxng_running_no_hace_nada_sin_searxng_url(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.delenv("SEARXNG_URL", raising=False)

    _ensure_searxng_running()


def test_ensure_searxng_running_importa_devtools_sin_repo_root_en_syspath() -> None:
    """Reproduce en un proceso aparte el escenario real del entry point
    instalado (.venv/bin/llm-lab): sys.path sin la raíz del repo, solo con
    src/ (vía editable install) — devtools/searxng/main.py vive fuera de
    src/. Sin el fix (agregar _REPO_ROOT a sys.path antes de importar), el
    import falla y el proceso cae en el aviso 'no se pudo importar
    devtools/searxng'. Con el fix, el import funciona y en cambio falla más
    adelante intentando resolver la URL fake — un error totalmente distinto
    que confirma que el import sí ocurrió."""
    code = (
        "import sys; "
        f"sys.path = [p for p in sys.path if p != {str(_REPO_ROOT)!r}]; "
        "import os; os.environ['SEARXNG_URL'] = 'http://localhost:1'; "
        "from local_llm_lab.cli.main import _ensure_searxng_running; "
        "_ensure_searxng_running()"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(_REPO_ROOT),
    )

    combined = result.stdout + result.stderr
    assert "no se pudo importar" not in combined, combined
