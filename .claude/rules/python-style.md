# Estilo Python — local-llm-lab

## Versión y tipado

- Python **3.14** exclusivamente (usar sintaxis moderna: `type` statement
  para alias, `X | Y` en vez de `Optional`/`Union`, generics sin `TypeVar`
  explícito cuando 3.14 lo permite).
- Tipado estricto en todo `src/`. `mypy --strict` sin errores.
- `Any` prohibido salvo interoperar con una librería de terceros sin stubs
  (ej. algún kwarg dinámico de `llama-cpp-python`) — en ese caso, aislar el
  `Any` en el punto exacto de la llamada, no propagarlo.

## Formato

- `ruff format` como formateador único (reemplaza black). Config en
  `pyproject.toml`.
- `ruff check` como linter único. Reglas: `E`, `F`, `I` (imports), `UP`
  (pyupgrade), `B` (bugbear), `SIM` (simplify).
- Line length 88 (default de ruff format), salvo que el usuario pida 80
  explícitamente para este repo — por defecto se respeta el default de la
  herramienta.
- 4 espacios de indentación (estándar Python, no 2).
- Docstrings solo en funciones públicas de `router/`, `backends/` y `cli/`
  cuando el comportamiento no es obvio desde la firma tipada. Una línea.
  Nunca docstrings multi-párrafo — si hace falta explicar tanto, la función
  está haciendo demasiado.

## Nomenclatura

```text
snake_case.py           # archivos y módulos
snake_case               # funciones, variables
PascalCase                # clases
UPPER_SNAKE_CASE          # constantes de módulo
```

## Estructura de módulo

- Un archivo por responsabilidad clara (`router.py`, `llama_cpp_backend.py`,
  `token_counter.py`), no un `utils.py` general.
- Imports absolutos dentro de `core` (`from core.router
  import LLMRouter`), nunca relativos con `..`.

## Errores y validación

- Validar solo en los bordes: CLI (input del usuario) y carga de config
  (`models.toml`). El código interno del router confía en los tipos que ya
  validó la config — no revalida en cada capa.
- Excepciones específicas del dominio (`ModelNotFoundError`,
  `BackendLoadError`), no `Exception` genérica ni códigos de error mágicos.

## Dependencias

- Gestión con `uv`. Nunca `pip install` manual en este repo — todo pasa por
  `pyproject.toml` + `uv sync` / `uv add`.
- Antes de agregar una dependencia nueva, evaluar si stdlib o una ya
  instalada la resuelve (ver `kiss-solid.md`).

## Extensión para `server/` (Django, stack de UI)

Todo lo de arriba aplica igual en `server/` — mismo target de Python,
mismo `ruff`/`mypy --strict` (corridos desde la raíz sobre `src server`),
mismas reglas de nomenclatura. Diferencias puntuales:

- **`server/llm/services/*.py` son funciones puras**, sin importar nada de
  `django.*` — reciben tipos de `core.*` y devuelven tipos propios
  (`ChatEvent`, dataclasses). `server/llm/views.py` es la única capa que
  conoce `HttpRequest`/`JsonResponse`/`StreamingHttpResponse`.
- **`Any` para librerías sin stubs de Django**: `django-stubs` cubre la
  mayoría del framework, pero algunas piezas (`daphne`, ciertos internals
  de `StreamingHttpResponse`) no tienen stubs — mismo criterio que
  `llama-cpp-python`: aislar el `# type: ignore[import-untyped]` en el
  import exacto, nunca propagar `Any` más allá de ese punto (ver
  `server/run_sidecar.py` para el patrón).
- **Tests de `server/llm/tests/` en español, mismo estilo** que
  `tests/unit/` — ver `.claude/rules/testing.md` para el detalle
  específico de qué se mockea en este stack.
