# local-llm-lab

Laboratorio para correr LLMs open source livianos en local (CPU/RAM, sin GPU
dedicada) desde Python, con un router extensible por modelo y un CLI de
benchmark para comparar tokens/segundo, tiempo de prefill y calidad básica
de respuesta entre modelos.

## Por qué existe

Investigación previa (ver `.claude/rules/research-context.md`) concluyó que
para tareas sencillas de chat/asistente, en una laptop sin GPU dedicada con
32GB+ RAM, los mejores candidatos son modelos 3B-8B cuantizados en GGUF
(Qwen3-4B, Qwen3-8B, Phi-4-mini, Gemma). Este proyecto es el lugar para
probarlos en la práctica y medir cuál rinde mejor en el hardware real del
usuario, en lugar de confiar solo en benchmarks de terceros.

## Requisitos

- Python 3.14
- [uv](https://docs.astral.sh/uv/) como gestor de entorno/dependencias
- Modelos GGUF descargados manualmente en `models/` (no se versionan en git)

## Setup

```bash
uv sync
```

## Uso

```bash
# listar modelos configurados
uv run llm-lab list

# chat con un modelo puntual (usa el router, default: gemma4-e2b)
uv run llm-lab chat --model qwen3-4b --system-file AGENTS.md

# benchmark de uno o varios modelos
uv run llm-lab bench --model qwen3-4b --model qwen3-8b --prompt-file tmp/prompt.txt

# chat interactivo en GPU con shell habilitado y personalidad Jarvis (sugerido)
uv run llm-lab chat --model gemma4-e2b --device gpu --interactive --allow-shell --agent jarvis
```

### Personalidades (`--agent`)

El tono de respuesta se controla con `--agent` (o la variable de entorno
`LLM_LAB_AGENT`): `jarvis`, `tars` o `gemma` (default, neutral). Ver
`src/local_llm_lab/personas/`.

## Estructura

```
src/local_llm_lab/
  router/       # LLMRouter: selecciona backend+modelo por nombre lógico
  backends/     # Adaptadores por runtime (llama_cpp hoy; extensible a otros)
  benchmark/    # Medición de tok/s, prefill, uso de memoria
  cli/          # Entry points de Typer/argparse
  config/       # Definición de modelos disponibles (YAML/TOML)
tests/
  unit/         # Tests aislados (mocks de backend)
  integration/  # Tests contra modelos reales (requieren GGUF descargado, skip si falta)
.claude/
  rules/        # KISS, SOLID, estilo Python, contexto de investigación
  skills/       # Skills invocables para tareas repetibles del proyecto
  agents/       # Definiciones de subagentes específicos del proyecto
```

Ver `CLAUDE.md` para las reglas de desarrollo obligatorias del proyecto.
