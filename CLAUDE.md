# CLAUDE.md — local-llm-lab

Proyecto Python 3.14. Reglas específicas de este repo — complementan (no
reemplazan) las reglas globales del usuario en `~/.claude/CLAUDE.md`.

## Qué es este proyecto

App de escritorio multiplataforma (Windows/Linux/Mac) para correr LLMs
open source locales (GGUF vía llama-cpp-python) con chat y benchmark de
eficiencia (tok/s, tiempo total, texto completo de respuesta). Soporta CPU
y GPU (offload CUDA) y modo thinking on/off en modelos que lo soportan
(familia Qwen3). Contexto completo de la investigación que originó este
proyecto: `.claude/rules/research-context.md`. Casos de uso reales de la
comunidad que motivan hacia dónde llevar el proyecto:
`.claude/rules/use-cases-research.md`.

El proyecto es un **mono-repo**: **Tauri v2 + React 19** como shell y
frontend, con un **servidor Django** (`server/llm/`) que expone toda la
lógica (router, backends, memoria, shell, benchmark) vía HTTP + SSE,
lanzado por Tauri como sidecar empaquetado (PyInstaller). No existe CLI —
la única interfaz es esta app de escritorio. Contexto completo de esta
arquitectura, decisiones de diseño y bugs reales ya resueltos:
`.claude/rules/ui-stack-architecture.md`.

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
- `shell-execution.md` — diseño y capas de seguridad de la ejecución de comandos vía `RUN:`
- `memory.md` — diseño de la memoria persistente del chat (`REMEMBER:`), por qué SQLite+FTS5 y no un grafo
- `ui-stack-architecture.md` — mono-repo Tauri v2 + React 19 + Django: por qué, estructura, contrato HTTP/SSE, decisiones de diseño y bugs reales ya resueltos (leer antes de tocar `ui/`, `server/` o `src-tauri/`)
- `frontend-style.md` — convenciones TypeScript/React de `ui/`, incluyendo el bug real de closures impuros en `setState` y cómo evitarlo

## Principios no negociables

1. **TDD**: test primero, implementación después. Ningún método nuevo del router o backend sin test que lo cubra antes del código de producción.
2. **KISS**: no agregar abstracción para un futuro hipotético. El router soporta hoy `llama-cpp-python`; no se agregan interfaces para runtimes que no se van a usar todavía.
3. **SOLID pragmático**: separación de responsabilidades donde reduce acoplamiento real (Backend vs Router vs Config vs Servicios de orquestación HTTP), no por dogma. Ver `kiss-solid.md` para el balance concreto.
4. **Tipado estricto**: type hints completos, sin `Any` salvo interoperar con librerías de terceros sin stubs. `mypy --strict` limpio.
5. **Zero-tolerance** para errores de lint/tipos antes de considerar una tarea terminada.
6. **Archivos temporales** en `./tmp/` del proyecto (gitignoreado), nunca en `/tmp/` del sistema.
7. **Sin comentarios explicativos de "qué hace el código"** — nombres claros lo dicen. Comentarios solo para el "por qué" no obvio (ver regla global).

## Comandos

```bash
uv sync                          # instalar dependencias Python (paquete único, ya no hay workspace)
pnpm install                     # dependencias de ui/

uv run pytest                    # correr tests (server/llm/tests/)
uv run ruff check .              # lint
uv run ruff format .             # formato
uv run mypy server               # type check

# Server Django solo (dev, sin autoreload para no perder cache de modelos)
PYTHONPATH="server" uv run daphne -b 127.0.0.1 -p 8000 server.asgi:application

# Frontend solo
pnpm --filter ui dev

# App Tauri completa (lanza Vite + sidecar automáticamente)
pnpm tauri dev

pnpm --filter ui exec tsc -b                # typecheck frontend
pnpm --filter ui run lint                   # oxlint
pnpm --filter ui exec playwright test       # e2e contra backend real, sin mocks

# Sidecar (PyInstaller) — regenerar tras tocar server/
cd server && ./build_sidecar.sh
```

Recompilar `llama-cpp-python` con CUDA si el offload a GPU falla con
"build CPU-only" (requiere `nvcc`/CUDA toolkit y `cmake` instalados):

```bash
CMAKE_ARGS="-DGGML_CUDA=on" uv pip install llama-cpp-python --force-reinstall --no-cache-dir
```

## Pre-commit checklist de este repo

- [ ] `uv run pytest` — 100% passing
- [ ] `uv run ruff check .` — sin errores
- [ ] `uv run ruff format --check .` — sin diffs pendientes
- [ ] `uv run mypy server` — sin errores
- [ ] Archivos temporales en `./tmp/`, no en `/tmp/`
- [ ] Modelos GGUF nuevos documentados en `server/llm/config/models.toml`, no hardcodeados en código
- [ ] Si se tocó `ui/`: `pnpm --filter ui exec tsc -b` y `pnpm --filter ui run lint` sin errores
- [ ] Si se tocó `ui/`, `server/` o `src-tauri/`: verificación end-to-end con modelo real (no solo `FakeBackend`) — ver checklist completo en `.claude/rules/ui-stack-architecture.md`

## Convención de modelos

Cada modelo soportado se declara como entrada en
`server/llm/config/models.toml` (nombre lógico, path relativo a
`models/`, contexto máximo, parámetros de carga). El router resuelve el
nombre lógico a esa config — nunca se hardcodea un path de modelo dentro del
código del router.

## Estructura de `server/llm/` (post-migración desde `src/core/`)

El código antes vivía en `src/core/` (paquete separado, compartido entre un
CLI Typer y el servidor Django vía uv workspace). El CLI se eliminó — la
única interfaz es la app de escritorio — así que todo colapsó a un solo
paquete Python dentro de `server/llm/`, separando dominio de orquestación:

```
server/llm/
  router/         # LLMRouter: resuelve nombre lógico -> backend
  backends/       # Adaptador llama-cpp-python
  benchmark/      # Medición de tok/s, prefill
  memory/         # SQLite+FTS5 para REMEMBER:
  shell/          # Blocklist + ejecución RUN:, tools de IP/clima/búsqueda
  config/         # models.toml, .env, prompts de tools (config/tools/*.md)
  personalities/  # Personas del chat (jarvis, tars, gemma)
  services/       # Orquestación HTTP: chat_turn, device, router_singleton,
                  # shell_confirm, system_prompt — únicos módulos que conectan
                  # el dominio de arriba con las vistas Django
  views.py        # Delgadas: parsean request, llaman a services/, serializan
  tests/          # Tests de todo lo anterior (unit + servicios)
```

Regla al agregar código nuevo: si es lógica de dominio (no sabe nada de
HTTP/Django), va en uno de los paquetes de dominio, no en `services/`. Si
orquesta una request HTTP completa (arma el flujo que llama `views.py`), va
en `services/`. Ver `.claude/rules/kiss-solid.md` para la señal de cuándo
esta separación se está rompiendo.
