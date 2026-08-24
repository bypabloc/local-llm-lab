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

- Mínimo 80% en `src/local_llm_lab/router/`, `backends/`, `benchmark/`
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
uv run pytest                    # todo
uv run pytest tests/unit         # solo unit, rápido, sin modelos reales
uv run pytest tests/integration  # requiere modelos descargados, más lento
uv run pytest --cov=src/local_llm_lab --cov-report=term-missing
```
