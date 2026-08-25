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

Además del CLI, el proyecto es un **mono-repo con UI de escritorio**
multiplataforma (Windows/Linux/Mac): **Tauri v2 + React 19** como shell y
frontend, con un **servidor Django** que expone la misma lógica del CLI vía
HTTP + SSE, lanzado por Tauri como sidecar empaquetado (PyInstaller). El
CLI original (`llm-lab chat/bench/list`) sigue existiendo y funcionando sin
cambios — la UI es una segunda forma de usar el mismo `src/core/`, no un
reemplazo. Contexto completo de esta arquitectura, decisiones de diseño y
bugs reales ya resueltos: `.claude/rules/ui-stack-architecture.md`.

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
- `ui-stack-architecture.md` — mono-repo Tauri v2 + React 19 + Django: por qué, estructura, contrato HTTP/SSE, decisiones de diseño y bugs reales ya resueltos (leer antes de tocar `ui/`, `server/` o `src-tauri/`)
- `frontend-style.md` — convenciones TypeScript/React de `ui/`, incluyendo el bug real de closures impuros en `setState` y cómo evitarlo

## Principios no negociables

1. **TDD**: test primero, implementación después. Ningún método nuevo del router o backend sin test que lo cubra antes del código de producción.
2. **KISS**: no agregar abstracción para un futuro hipotético. El router soporta hoy `llama-cpp-python`; no se agregan interfaces para runtimes que no se van a usar todavía.
3. **SOLID pragmático**: separación de responsabilidades donde reduce acoplamiento real (Backend vs Router vs Config), no por dogma. Ver `kiss-solid.md` para el balance concreto.
4. **Tipado estricto**: type hints completos, sin `Any` salvo interoperar con librerías de terceros sin stubs. `mypy --strict` limpio.
5. **Zero-tolerance** para errores de lint/tipos antes de considerar una tarea terminada.
6. **Archivos temporales** en `./tmp/` del proyecto (gitignoreado), nunca en `/tmp/` del sistema.
7. **Sin comentarios explicativos de "qué hace el código"** — nombres claros lo dicen. Comentarios solo para el "por qué" no obvio (ver regla global).

## Comandos — CLI y core (`src/core/`)

```bash
uv sync                          # instalar dependencias (solo paquete core)
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

## Comandos — stack de UI (`ui/`, `server/`, `src-tauri/`)

Ver `.claude/rules/ui-stack-architecture.md` para el detalle completo
(prerequisitos de sistema, arquitectura, decisiones de diseño). Resumen:

```bash
uv sync --all-packages           # instala core + server (uv sync solo NO alcanza)
pnpm install                     # dependencias de ui/

# Server Django solo (dev)
PYTHONPATH="src:server" uv run daphne -b 127.0.0.1 -p 8000 server.asgi:application

# Frontend solo
pnpm --filter ui dev

# App Tauri completa (lanza Vite + sidecar automáticamente)
pnpm tauri dev

# Tests de este stack
uv run pytest                              # incluye server/llm/tests/
pnpm --filter ui exec tsc -b                # typecheck frontend
pnpm --filter ui run lint                   # oxlint
pnpm --filter ui exec playwright test       # e2e contra backend real, sin mocks

# Sidecar (PyInstaller) — regenerar tras tocar server/ o src/core/
cd server && ./build_sidecar.sh
```

## Pre-commit checklist de este repo

- [ ] `uv run pytest` — 100% passing (cubre `src/core/` y `server/`)
- [ ] `uv run ruff check .` — sin errores
- [ ] `uv run ruff format --check .` — sin diffs pendientes
- [ ] `uv run mypy src server` — sin errores
- [ ] Archivos temporales en `./tmp/`, no en `/tmp/`
- [ ] Modelos GGUF nuevos documentados en `src/core/config/models.toml`, no hardcodeados en código
- [ ] Si se tocó `ui/`: `pnpm --filter ui exec tsc -b` y `pnpm --filter ui run lint` sin errores
- [ ] Si se tocó `ui/`, `server/` o `src-tauri/`: verificación end-to-end con modelo real (no solo `FakeBackend`) — ver checklist completo en `.claude/rules/ui-stack-architecture.md`

## Convención de modelos

Cada modelo soportado se declara como entrada en
`src/core/config/models.toml` (nombre lógico, path relativo a
`models/`, contexto máximo, parámetros de carga). El router resuelve el
nombre lógico a esa config — nunca se hardcodea un path de modelo dentro del
código del router o del CLI.
