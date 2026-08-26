# local-llm-lab

App de escritorio (Tauri v2 + React 19 + Django) para correr LLMs open
source livianos en local (CPU/GPU) desde una UI de chat, con benchmark
integrado de tokens/segundo, tiempo de prefill y calidad básica de
respuesta entre modelos.

## Por qué existe

Investigación previa (ver `.claude/rules/research-context.md`) concluyó que
para tareas sencillas de chat/asistente, modelos 3B-8B cuantizados en GGUF
(Qwen3-4B, Qwen3-8B, Phi-4-mini, Gemma) son el mejor punto de partida. Este
proyecto es el lugar para probarlos en la práctica y medir cuál rinde mejor
en el hardware real del usuario, en lugar de confiar solo en benchmarks de
terceros. Arquitectura completa del stack de UI: `.claude/rules/ui-stack-architecture.md`.

## Requisitos

- Python 3.14 + [uv](https://docs.astral.sh/uv/)
- Node.js + [pnpm](https://pnpm.io/)
- Rust (vía `rustup`) + dependencias nativas de Tauri v2
- Modelos GGUF descargados manualmente en `models/` (no se versionan en git)

## Setup

```bash
uv sync
pnpm install
```

## Uso

```bash
# App Tauri completa (lanza Vite + servidor Django automáticamente)
pnpm tauri dev

# Servidor Django solo (dev, sin autoreload)
PYTHONPATH="server" uv run daphne -b 127.0.0.1 -p 8000 server.asgi:application

# Frontend solo
pnpm --filter ui dev
```

### Personalidades (`agent`)

El tono de respuesta se controla eligiendo `agent` en la request de chat:
`jarvis`, `tars` o `gemma` (default, neutral). Ver `server/llm/personalities/`.

## Estructura

```
server/
  llm/
    router/       # LLMRouter: selecciona backend+modelo por nombre lógico
    backends/     # Adaptadores por runtime (llama_cpp hoy; extensible a otros)
    benchmark/    # Medición de tok/s, prefill, uso de memoria
    memory/       # Memoria persistente del chat (SQLite+FTS5)
    shell/        # Ejecución de comandos vía RUN:, tools de IP/clima/búsqueda
    config/       # models.toml, .env, prompts de tools
    personalities/ # Personas del chat (jarvis, tars, gemma)
    services/     # Orquestación HTTP: chat_turn, device, router_singleton, etc.
    views.py      # Endpoints Django (delgados, delegan a services/)
    tests/        # Tests del stack completo (unit + integración de servicios)
  server/         # settings.py, urls.py, asgi.py
ui/               # React 19 + Vite + TypeScript
src-tauri/        # Shell nativo Tauri v2
.claude/
  rules/          # KISS, SOLID, estilo Python/TS, arquitectura, contexto de investigación
  skills/         # Skills invocables para tareas repetibles del proyecto
```

Ver `CLAUDE.md` para las reglas de desarrollo obligatorias del proyecto.
