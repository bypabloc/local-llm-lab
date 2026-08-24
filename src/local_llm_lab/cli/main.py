import dataclasses
import json
import time
from pathlib import Path
from typing import Annotated

import typer

from local_llm_lab.backends.errors import BackendLoadError
from local_llm_lab.backends.llama_cpp_backend import LlamaCppBackend
from local_llm_lab.backends.protocol import ChatMessage, LLMBackend
from local_llm_lab.benchmark.runner import run_benchmark
from local_llm_lab.config.models import load_model_configs
from local_llm_lab.personas import Persona, get_persona, resolve_agent_name, wrap_banner
from local_llm_lab.router.errors import ModelNotFoundError
from local_llm_lab.router.llm_router import LLMRouter
from local_llm_lab.shell.runner import (
    SYSTEM_PROMPT_SUFFIX,
    extract_run_command,
    run_with_confirmation,
)

app = typer.Typer(help="local-llm-lab: router + benchmark de LLMs locales")

DeviceOption = Annotated[
    str,
    typer.Option(
        "--device",
        help="Dónde correr el modelo: 'cpu' o 'gpu' (offload completo a GPU vía CUDA)",
    ),
]

AgentOption = Annotated[
    str | None,
    typer.Option(
        "--agent",
        help=(
            "Personalidad de respuesta: 'jarvis', 'tars' o 'gemma' (default). "
            "Si no se indica, usa la variable de entorno LLM_LAB_AGENT."
        ),
    ),
]


def _load_persona(agent: str | None) -> Persona:
    return get_persona(resolve_agent_name(agent))


def _apply_persona_to_system(persona: Persona, system: str) -> str:
    if not persona.system_prefix:
        return system
    return f"{persona.system_prefix}\n\n{system}" if system else persona.system_prefix


# ponytail: -1 = todas las capas a GPU (offload completo). Simple porque hoy
# solo se soportan dos modos, no un control fino de cuántas capas offloadear.
_GPU_LAYERS_FULL_OFFLOAD = -1


def _build_router(device: str) -> LLMRouter:
    if device not in ("cpu", "gpu"):
        typer.echo(
            f"Error: --device debe ser 'cpu' o 'gpu', recibido '{device}'", err=True
        )
        raise typer.Exit(code=1)

    configs = load_model_configs()
    if device == "gpu":
        gpu_layers = _GPU_LAYERS_FULL_OFFLOAD
        configs = {
            name: dataclasses.replace(config, n_gpu_layers=gpu_layers)
            for name, config in configs.items()
        }
    return LLMRouter(configs, backend_factory=LlamaCppBackend)


@app.command("list")
def list_models(device: DeviceOption = "cpu") -> None:
    """Lista los modelos configurados en config/models.toml."""
    router = _build_router(device)
    for name in router.available_models():
        typer.echo(name)


def _handle_run_command(response_text: str) -> str | None:
    """Si `response_text` propone un comando vía RUN:, lo confirma y ejecuta.

    Devuelve un resumen para inyectar de vuelta al historial (rol system),
    o None si no había comando que ejecutar.
    """
    command = extract_run_command(response_text)
    if command is None:
        return None

    typer.echo(f"\n>>> el modelo propone ejecutar: {command}")
    confirmed = typer.confirm(">>> ¿ejecutar este comando?", default=False)
    outcome = run_with_confirmation(command, confirm=confirmed)

    if outcome.blocked_reason is not None:
        typer.echo(f">>> bloqueado: {outcome.blocked_reason}")
        return f"[comando bloqueado: {command} — motivo: {outcome.blocked_reason}]"
    if not outcome.executed:
        typer.echo(">>> no ejecutado (cancelado por el usuario)")
        return f"[comando no ejecutado: {command} — el usuario no confirmó]"

    typer.echo(
        f">>> salida (code={outcome.return_code}):\n{outcome.stdout}{outcome.stderr}"
    )
    return (
        f"[resultado de ejecutar '{command}': "
        f"code={outcome.return_code}, stdout={outcome.stdout!r}, "
        f"stderr={outcome.stderr!r}]"
    )


def _run_interactive(
    backend: LLMBackend,
    system: str,
    max_tokens: int,
    no_think: bool,
    device: str,
    model: str,
    allow_shell: bool,
    persona: Persona,
) -> None:
    typer.echo(
        wrap_banner(
            persona,
            f"--- chat interactivo con {model} [{device}] — 'exit' para salir ---",
        )
    )
    if allow_shell:
        typer.echo(">>> modo shell activo (comandos requieren tu confirmación)")
    effective_system = system + SYSTEM_PROMPT_SUFFIX if allow_shell else system
    history: list[ChatMessage] = []
    if effective_system:
        history.append({"role": "system", "content": effective_system})

    while True:
        try:
            user_input = typer.prompt("tú")
        except (EOFError, KeyboardInterrupt):
            typer.echo("\n--- fin del chat ---")
            return
        if user_input.strip().lower() == "exit":
            typer.echo("--- fin del chat ---")
            return

        content = f"{user_input} /no_think" if no_think else user_input
        history.append({"role": "user", "content": content})

        typer.echo(f"{model}: ", nl=False)
        start = time.perf_counter()
        chunks: list[str] = []
        for token in backend.stream_chat(history, max_tokens=max_tokens):
            typer.echo(token, nl=False)
            chunks.append(token)
        elapsed = time.perf_counter() - start
        typer.echo()
        typer.echo(f"--- tiempo={elapsed:.2f}s ---")

        response_text = "".join(chunks)
        history.append({"role": "assistant", "content": response_text})

        if allow_shell:
            run_summary = _handle_run_command(response_text)
            if run_summary is not None:
                history.append({"role": "system", "content": run_summary})


DEFAULT_MODEL = "gemma4-e2b"


@app.command("chat")
def chat(
    model: Annotated[
        str, typer.Option(help="Nombre lógico del modelo")
    ] = DEFAULT_MODEL,
    system_file: Annotated[
        Path | None, typer.Option(help="Archivo de system prompt (ej. AGENTS.md)")
    ] = None,
    message: Annotated[
        str, typer.Option(help="Mensaje del usuario")
    ] = "Hola, preséntate en una frase.",
    max_tokens: Annotated[int, typer.Option(help="Tope de tokens de respuesta")] = 1024,
    no_think: Annotated[
        bool,
        typer.Option(
            "--no-think",
            help="Desactiva el modo thinking en modelos que lo soportan (Qwen3)",
        ),
    ] = False,
    device: DeviceOption = "cpu",
    interactive: Annotated[
        bool,
        typer.Option(
            "--interactive",
            help="Modo REPL con historial y streaming en vez de un solo turno",
        ),
    ] = False,
    allow_shell: Annotated[
        bool,
        typer.Option(
            "--allow-shell",
            help=(
                "Permite que el modelo proponga comandos de shell (marcador RUN:) "
                "en modo --interactive. Requiere confirmación manual por comando "
                "y pasa por un blocklist — nunca se ejecuta nada sin tu 's'."
            ),
        ),
    ] = False,
    agent: AgentOption = None,
) -> None:
    """Envía un mensaje a un modelo (o abre un REPL con --interactive)."""
    persona = _load_persona(agent)
    router = _build_router(device)
    system = system_file.read_text(encoding="utf-8") if system_file else ""
    system = _apply_persona_to_system(persona, system)
    try:
        backend = router.get(model)
    except (ModelNotFoundError, BackendLoadError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if interactive:
        _run_interactive(
            backend, system, max_tokens, no_think, device, model, allow_shell, persona
        )
        return

    start = time.perf_counter()
    result = backend.generate(
        system=system, user=message, max_tokens=max_tokens, no_think=no_think
    )
    elapsed = time.perf_counter() - start
    typer.echo(wrap_banner(persona, f"--- {model} [{device}] ---"))
    typer.echo(result.text)
    typer.echo(
        f"--- tiempo={elapsed:.2f}s tokens(prompt={result.prompt_tokens}, "
        f"completion={result.completion_tokens}) ---"
    )


@app.command("bench")
def bench(
    model: Annotated[list[str], typer.Option(help="Modelo a benchmarkear (repetible)")],
    system_file: Annotated[Path | None, typer.Option()] = None,
    prompt: Annotated[str, typer.Option()] = "Resumí en 3 puntos qué es Python.",
    max_tokens: Annotated[int, typer.Option(help="Tope de tokens de respuesta")] = 1024,
    no_think: Annotated[
        bool,
        typer.Option(
            "--no-think",
            help="Desactiva el modo thinking en modelos que lo soportan (Qwen3)",
        ),
    ] = False,
    show_text: Annotated[
        bool, typer.Option(help="Imprime el texto completo de cada respuesta")
    ] = False,
    output: Annotated[
        Path | None, typer.Option(help="Guardar resultados (con texto) en JSON")
    ] = None,
    device: DeviceOption = "cpu",
    agent: AgentOption = None,
) -> None:
    """Compara tok/s, tiempo total y respuesta completa entre uno o varios modelos."""
    persona = _load_persona(agent)
    router = _build_router(device)
    system = system_file.read_text(encoding="utf-8") if system_file else ""
    system = _apply_persona_to_system(persona, system)
    results = []

    for name in model:
        try:
            backend = router.get(name)
        except (ModelNotFoundError, BackendLoadError) as exc:
            typer.echo(f"[{name}] error al cargar: {exc}", err=True)
            continue

        result = run_benchmark(
            name,
            backend,
            system=system,
            user=prompt,
            max_tokens=max_tokens,
            no_think=no_think,
        )
        results.append(result)
        typer.echo(
            wrap_banner(
                persona,
                f">>> {name:20s} [{device}] tiempo={result.total_seconds:6.2f}s "
                f"tok/s={result.tokens_per_second:6.2f} "
                f"tokens(prompt={result.prompt_tokens}, "
                f"completion={result.completion_tokens}) "
                f"[{result.rating}]",
            )
        )
        if show_text:
            typer.echo(f"--- respuesta {name} ---\n{result.text}\n")

        # ponytail: liberar antes del siguiente modelo, no al final del loop
        # — si no, N modelos comparados en GPU se acumulan en VRAM y el
        # último falla al cargar por falta de espacio (bug real observado).
        router.unload(name)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "model": r.model_name,
                "device": device,
                "tokens_per_second": r.tokens_per_second,
                "total_seconds": r.total_seconds,
                "prefill_seconds": r.prefill_seconds,
                "generation_seconds": r.generation_seconds,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "rating": r.rating,
                "no_think": r.no_think,
                "text": r.text,
            }
            for r in results
        ]
        output.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        typer.echo(f"Resultados guardados en {output}")


if __name__ == "__main__":
    app()
