# Testing — local-llm-lab

## TDD obligatorio

Test primero, implementación después, sin excepción para código nuevo en
`router/`, `backends/` o `benchmark/`. Ciclo rojo-verde-refactor.

## Qué se mockea y qué no

- **Unit tests (`tests/unit/`)**: el backend real (`llama-cpp-python`) se
  mockea siempre. El router y el CLI se testean contra un
  `FakeBackend`/`FakeLLM` en memoria que implementa el mismo protocolo. No
  se descarga ni carga un `.gguf` real en unit tests.
- **Integration tests (`tests/integration/`)**: corren contra un modelo
  GGUF real si existe en `models/`. Si el archivo no está presente, el test
  se **skipea** (no falla) con un mensaje claro — estos tests no son parte
  del CI por defecto, son para verificación manual local.

## Estructura

```python
# tests/unit/test_router.py
def test_router_resuelve_modelo_por_nombre_logico() -> None: ...
def test_router_lanza_model_not_found_si_no_existe_en_config() -> None: ...


# tests/integration/test_llama_cpp_backend_real.py
@pytest.mark.skipif(not MODEL_PATH.exists(), reason="modelo GGUF no descargado")
def test_genera_respuesta_con_modelo_real() -> None: ...
```

## Cobertura

- Mínimo 80% en `src/core/router/`, `backends/`, `benchmark/`
  (la lógica que decide y mide, no el CLI de parsing de argv que es
  mayormente I/O).
- No perseguir 100% en `cli/` — el valor ahí está en tests de integración
  manuales (correr el comando) más que en cobertura de líneas.

## Qué NO testear

- No testear que `llama-cpp-python` internamente genera texto correcto —
  eso es responsabilidad de esa librería, no de este proyecto.
- No escribir tests para getters/setters triviales o dataclasses sin
  lógica.

## Comando

```bash
uv run pytest                    # todo (incluye server/llm/tests/)
uv run pytest tests/unit         # solo unit de core, rápido, sin modelos reales
uv run pytest tests/integration  # requiere modelos descargados, más lento
uv run pytest server/llm/tests   # solo tests del stack de UI
uv run pytest --cov=src/core --cov-report=term-missing
```

## Testing del stack de UI (`server/llm/tests/`, `ui/e2e/`)

Mismo principio de TDD y mismo patrón Arrange-Act-Assert que el resto del
proyecto, con estas particularidades:

- **`server/llm/tests/fakes.py`** es una copia adaptada de
  `tests/unit/fakes.py` (mismo `FakeBackend`/`make_model_config`), no un
  import compartido — `server/` no debería depender de la carpeta
  `tests/` de `core`. Si `FakeBackend` cambia en `tests/unit/fakes.py`,
  revisar si el cambio también aplica acá.
- **Servicios de `llm/services/` se testean sin Django de por medio**
  cuando es posible (`test_system_prompt.py`, `test_chat_turn.py`) — son
  funciones puras, no necesitan `Client`/`AsyncClient`. Las vistas
  (`test_views_*.py`) sí usan `django.test.Client`/`AsyncClient`, con
  `pytest-django`/`pytest-asyncio`, pero siguen inyectando `FakeBackend`
  vía monkeypatch del `router_singleton` — nunca cargan un modelo GGUF
  real en estos tests.
- **`ui/e2e/*.spec.ts` (Playwright) corren contra el backend Django REAL**,
  no contra un mock — es la única capa de test que hubiera atrapado el
  bug real de un closure impuro en `useChatStream` (el stream backend
  funcionaba perfecto, pero el DOM nunca se actualizaba; invisible en
  tests unitarios de React y en curl). Requieren el server Django
  corriendo (`playwright.config.ts` levanta Vite solo, no Django). No
  reemplazan los tests unitarios — son la capa que confirma que las
  piezas conectan de verdad.
- **Verificación manual con modelo GGUF real** sigue siendo obligatoria
  antes de cerrar una tarea de este stack, igual que ya lo era para el
  CLI (`tests/integration/`) — ver checklist completo en
  `.claude/rules/ui-stack-architecture.md`.

```bash
uv run pytest server/llm/tests -v
pnpm --filter ui exec playwright test          # requiere backend Django corriendo
pnpm --filter ui exec playwright test --ui     # modo interactivo, útil para debug
```
