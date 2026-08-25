# CLAUDE.md — local-llm-lab

Proyecto Python 3.14. Reglas específicas de este repo — complementan (no
reemplazan) las reglas globales del usuario en `~/.claude/CLAUDE.md`.

## Qué es este proyecto

Router extensible para correr múltiples LLMs open source locales (GGUF vía
llama-cpp-python) desde Python, con CLI para benchmarking de eficiencia
(tok/s, tiempo total, texto completo de respuesta). Soporta CPU y GPU
(offload CUDA vía `--device`) y modo thinking on/off en modelos que lo
soportan (`--no-think`, familia Qwen3). Contexto completo de la
investigación que originó este proyecto: `.claude/rules/research-context.md`.
Casos de uso reales de la comunidad que motivan hacia dónde llevar el
proyecto: `.claude/rules/use-cases-research.md`.

## Hardware de referencia (donde se validó el proyecto)

RTX 4060 Laptop (8GB VRAM), 18 cores CPU, 32GB RAM. `llama-cpp-python`
compilado con soporte CUDA (`CMAKE_ARGS="-DGGML_CUDA=on"`). Con este
hardware, GPU da 3-7.5x más tok/s que CPU en los 4 modelos configurados —
ver `tmp/bench-*-cpu.json` y `tmp/bench-*-gpu.json` para las cifras medidas.

## Reglas de desarrollo obligatorias

Ver en detalle: `.claude/rules/`

- `kiss-solid.md` — KISS y SOLID aplicados a este codebase, con ejemplos concretos del router
- `python-style.md` — Python 3.14, tipado estricto, formato, convenciones
- `testing.md` — TDD, qué se mockea y qué no, estructura de tests
- `research-context.md` — resumen de la investigación de modelos/hardware que da contexto a las decisiones del proyecto
- `use-cases-research.md` — investigación de comunidad sobre para qué se usan realmente los LLMs locales, y qué features priorizar en este proyecto en base a eso
- `shell-execution.md` — diseño y capas de seguridad de la ejecución de comandos vía `--allow-shell`
- `memory.md` — diseño de la memoria persistente del chat (`REMEMBER:`), por qué SQLite+FTS5 y no un grafo

## Principios no negociables

1. **TDD**: test primero, implementación después. Ningún método nuevo del router o backend sin test que lo cubra antes del código de producción.
2. **KISS**: no agregar abstracción para un futuro hipotético. El router soporta hoy `llama-cpp-python`; no se agregan interfaces para runtimes que no se van a usar todavía.
3. **SOLID pragmático**: separación de responsabilidades donde reduce acoplamiento real (Backend vs Router vs Config), no por dogma. Ver `kiss-solid.md` para el balance concreto.
4. **Tipado estricto**: type hints completos, sin `Any` salvo interoperar con librerías de terceros sin stubs. `mypy --strict` limpio.
5. **Zero-tolerance** para errores de lint/tipos antes de considerar una tarea terminada.
6. **Archivos temporales** en `./tmp/` del proyecto (gitignoreado), nunca en `/tmp/` del sistema.
7. **Sin comentarios explicativos de "qué hace el código"** — nombres claros lo dicen. Comentarios solo para el "por qué" no obvio (ver regla global).

## Comandos

```bash
uv sync                          # instalar dependencias
uv run pytest                    # correr tests
uv run ruff check .              # lint
uv run ruff format .             # formato
uv run mypy src                  # type check
uv run llm-lab list --device gpu                       # listar modelos, resolviendo config para GPU
uv run llm-lab chat --model X --device gpu --no-think   # chat puntual
uv run llm-lab bench --model X --device gpu --show-text --output tmp/out.json  # benchmark con texto completo
```

Recompilar `llama-cpp-python` con CUDA si `--device gpu` falla con
"build CPU-only" (requiere `nvcc`/CUDA toolkit y `cmake` instalados):

```bash
CMAKE_ARGS="-DGGML_CUDA=on" uv pip install llama-cpp-python --force-reinstall --no-cache-dir
```

## Pre-commit checklist de este repo

- [ ] `uv run pytest` — 100% passing
- [ ] `uv run ruff check .` — sin errores
- [ ] `uv run ruff format --check .` — sin diffs pendientes
- [ ] `uv run mypy src` — sin errores
- [ ] Archivos temporales en `./tmp/`, no en `/tmp/`
- [ ] Modelos GGUF nuevos documentados en `src/local_llm_lab/config/models.toml`, no hardcodeados en código

## Convención de modelos

Cada modelo soportado se declara como entrada en
`src/local_llm_lab/config/models.toml` (nombre lógico, path relativo a
`models/`, contexto máximo, parámetros de carga). El router resuelve el
nombre lógico a esa config — nunca se hardcodea un path de modelo dentro del
código del router o del CLI.
