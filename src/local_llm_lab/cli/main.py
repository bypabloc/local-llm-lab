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
from local_llm_lab.config.dotenv import load_dotenv
from local_llm_lab.config.models import load_model_configs
from local_llm_lab.config.tools import load_tool_prompt
from local_llm_lab.personalities import (
    Persona,
    get_persona,
    resolve_agent_name,
    wrap_banner,
)
from local_llm_lab.router.errors import ModelNotFoundError
from local_llm_lab.router.llm_router import LLMRouter
from local_llm_lab.shell.location import (
    extract_ip_query,
    extract_location_query,
    extract_weather_query,
    get_location,
    get_public_ip,
    get_weather_for_current_location,
)
from local_llm_lab.shell.runner import extract_run_command, run_with_confirmation
from local_llm_lab.shell.web_search import extract_search_query, search_web

load_dotenv(Path.cwd() / ".env")

app = typer.Typer(help="local-llm-lab: router + benchmark de LLMs locales")


def _detect_device() -> str:
    """gpu si llama-cpp-python tiene soporte CUDA/Metal compilado, sino cpu."""
    from llama_cpp import llama_supports_gpu_offload

    return "gpu" if llama_supports_gpu_offload() else "cpu"


DeviceOption = Annotated[
    str | None,
    typer.Option(
        "--device",
        help=(
            "Dónde correr el modelo: 'cpu' o 'gpu'. Sin indicar, se autodetecta "
            "según si llama-cpp-python tiene soporte CUDA compilado."
        ),
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


def _resolve_device(device: str | None) -> str:
    if device is None:
        return _detect_device()
    if device not in ("cpu", "gpu"):
        typer.echo(
            f"Error: --device debe ser 'cpu' o 'gpu', recibido '{device}'", err=True
        )
        raise typer.Exit(code=1)
    return device


def _build_router(device: str) -> LLMRouter:
    configs = load_model_configs()
    if device == "gpu":
        gpu_layers = _GPU_LAYERS_FULL_OFFLOAD
        configs = {
            name: dataclasses.replace(config, n_gpu_layers=gpu_layers)
            for name, config in configs.items()
        }
    return LLMRouter(configs, backend_factory=LlamaCppBackend)


@app.command("list")
def list_models(device: DeviceOption = None) -> None:
    """Lista los modelos configurados en config/models.toml."""
    router = _build_router(_resolve_device(device))
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


def _handle_search_query(response_text: str) -> str | None:
    """Si `response_text` propone una búsqueda vía SEARCH:, la ejecuta.

    Devuelve un resumen para inyectar de vuelta al historial (rol system),
    o None si no había consulta que buscar. No requiere confirmación manual
    — es de solo lectura, no ejecuta nada en el sistema del usuario.
    """
    query = extract_search_query(response_text)
    if query is None:
        return None

    typer.echo(f"\n>>> buscando en internet: {query}")
    outcome = search_web(query)

    if outcome.error is not None:
        typer.echo(f">>> error de búsqueda: {outcome.error}")
        return f"[búsqueda '{query}' falló: {outcome.error}]"

    if not outcome.results:
        typer.echo(">>> sin resultados")
        return f"[búsqueda '{query}' no encontró resultados]"

    for result in outcome.results:
        typer.echo(f"  - {result.title} ({result.url})\n    {result.snippet}")

    formatted = "\n".join(
        f"- {r.title} ({r.url}): {r.snippet}" for r in outcome.results
    )
    return f"[resultados de búsqueda para '{query}':\n{formatted}]"


def _handle_ip_query(response_text: str) -> str | None:
    """Si `response_text` propone consultar la IP pública vía IP:, la resuelve.

    Devuelve un resumen para inyectar de vuelta al historial (rol system),
    o None si no había marcador. Es de solo lectura.
    """
    if not extract_ip_query(response_text):
        return None

    typer.echo("\n>>> consultando IP pública")
    outcome = get_public_ip()

    if outcome.error is not None:
        typer.echo(f">>> error al consultar IP: {outcome.error}")
        return f"[consulta de IP falló: {outcome.error}]"

    typer.echo(f"  - {outcome.ip}")
    return f"[IP pública actual: {outcome.ip}]"


def _handle_location_query(response_text: str) -> str | None:
    """Si `response_text` propone consultar la ubicación vía LOCATION:, la resuelve.

    Devuelve un resumen para inyectar de vuelta al historial (rol system),
    o None si no había marcador. Es de solo lectura.
    """
    if not extract_location_query(response_text):
        return None

    typer.echo("\n>>> consultando ubicación aproximada")
    outcome = get_location()

    if outcome.error is not None:
        typer.echo(f">>> error al consultar ubicación: {outcome.error}")
        return f"[consulta de ubicación falló: {outcome.error}]"

    typer.echo(f"  - {outcome.city}, {outcome.country}")
    return f"[ubicación aproximada actual: {outcome.city}, {outcome.country}]"


def _handle_weather_query(response_text: str) -> str | None:
    """Si `response_text` propone consultar clima vía WEATHER:, lo resuelve.

    Encadena IP pública -> geolocalización -> clima (Open-Meteo). Devuelve un
    resumen para inyectar de vuelta al historial (rol system), o None si no
    había marcador. Es de solo lectura, no requiere confirmación manual.
    """
    if not extract_weather_query(response_text):
        return None

    typer.echo("\n>>> consultando ubicación y clima actual")
    outcome = get_weather_for_current_location()

    if outcome.error is not None:
        typer.echo(f">>> error al consultar clima: {outcome.error}")
        return f"[consulta de clima falló: {outcome.error}]"

    typer.echo(
        f"  - {outcome.city}, {outcome.country}: "
        f"{outcome.temperature_celsius}°C (código {outcome.weather_code})"
    )
    return (
        f"[clima actual en {outcome.city}, {outcome.country}: "
        f"{outcome.temperature_celsius}°C, código de clima {outcome.weather_code}]"
    )


def _ensure_searxng_running() -> None:
    """Si SEARXNG_URL apunta a una instancia local, la levanta con Docker si hace falta.

    Import perezoso: `devtools/` es tooling de desarrollo fuera de src/, no una
    dependencia del paquete instalable — su ausencia no debe romper el chat.
    """
    import os

    url = os.environ.get("SEARXNG_URL")
    if not url:
        return

    try:
        from devtools.searxng.main import SearxngUnavailableError, ensure_running
    except ImportError:
        typer.echo(
            ">>> aviso: no se pudo importar devtools/searxng "
            "(¿corriste el comando fuera de la raíz del repo?), "
            "sigo sin auto-levantar SearXNG"
        )
        return

    try:
        ensure_running(url)
    except SearxngUnavailableError as exc:
        typer.echo(f"Error: no se pudo levantar SearXNG en {url}: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def _generate_and_echo(
    backend: LLMBackend, history: list[ChatMessage], persona: Persona, max_tokens: int
) -> str:
    """Genera la respuesta del modelo, la imprime en streaming y la devuelve"""
    typer.echo(f"{persona.name}: ", nl=False)
    start = time.perf_counter()
    chunks: list[str] = []
    for token in backend.stream_chat(history, max_tokens=max_tokens):
        typer.echo(token, nl=False)
        chunks.append(token)
    elapsed = time.perf_counter() - start
    typer.echo()
    typer.echo(f"--- tiempo={elapsed:.2f}s ---")
    return "".join(chunks)


def _run_interactive(
    backend: LLMBackend,
    system: str,
    max_tokens: int,
    no_think: bool,
    device: str,
    model: str,
    allow_shell: bool,
    allow_search: bool,
    persona: Persona,
) -> None:
    if allow_search:
        _ensure_searxng_running()

    typer.echo(
        wrap_banner(
            persona,
            f"--- chat interactivo con {model} [{device}] — 'exit' para salir ---",
        )
    )
    if not allow_shell:
        typer.echo(">>> modo shell desactivado (--disable-shell)")
    if not allow_search:
        typer.echo(">>> búsqueda web desactivada (--disable-search)")
    effective_system = system
    tool_names = [
        "IP: — IP pública actual",
        "LOCATION: — ubicación aproximada actual (ciudad/país)",
        "WEATHER: — clima actual",
    ]
    if allow_shell:
        tool_names.append("RUN: <comando> — ejecutar un comando de shell")
    if allow_search:
        tool_names.append("SEARCH: <consulta> — buscar en internet")
    effective_system += (
        "\n\nHerramientas disponibles (usalas escribiendo la línea exacta "
        "cuando corresponda):\n" + "\n".join(f"- {t}" for t in tool_names)
    )
    effective_system += load_tool_prompt("weather")
    if allow_shell:
        effective_system += load_tool_prompt("shell")
    if allow_search:
        effective_system += load_tool_prompt("search")
    history: list[ChatMessage] = []
    if effective_system:
        history.append({"role": "system", "content": effective_system})

    while True:
        try:
            user_input = typer.prompt("tú")
        except (EOFError, KeyboardInterrupt):
            typer.echo("\n--- fin del chat ---")
            return
        # ponytail: la terminal a veces manda bytes no-UTF8 (WSL2 + clipboard
        # de Windows), que Python decodifica con surrogateescape y rompen al
        # re-encodear en el tokenizer. errors="replace" los descarta acá,
        # en el borde de entrada, antes de que lleguen al backend.
        user_input = user_input.encode("utf-8", errors="replace").decode("utf-8")
        if user_input.strip().lower() == "exit":
            typer.echo("--- fin del chat ---")
            return

        content = f"{user_input} /no_think" if no_think else user_input
        history.append({"role": "user", "content": content})

        response_text = _generate_and_echo(backend, history, persona, max_tokens)
        history.append({"role": "assistant", "content": response_text})

        # ponytail: una sola ronda de seguimiento automático, no un loop —
        # evita que el modelo encadene tools indefinidamente sin que el
        # usuario vuelva a intervenir.
        used_a_tool = False

        if allow_shell:
            run_summary = _handle_run_command(response_text)
            if run_summary is not None:
                history.append({"role": "system", "content": run_summary})
                used_a_tool = True

        if allow_search:
            search_summary = _handle_search_query(response_text)
            if search_summary is not None:
                history.append({"role": "system", "content": search_summary})
                used_a_tool = True

        ip_summary = _handle_ip_query(response_text)
        if ip_summary is not None:
            history.append({"role": "system", "content": ip_summary})
            used_a_tool = True

        location_summary = _handle_location_query(response_text)
        if location_summary is not None:
            history.append({"role": "system", "content": location_summary})
            used_a_tool = True

        weather_summary = _handle_weather_query(response_text)
        if weather_summary is not None:
            history.append({"role": "system", "content": weather_summary})
            used_a_tool = True

        if used_a_tool:
            followup_text = _generate_and_echo(backend, history, persona, max_tokens)
            history.append({"role": "assistant", "content": followup_text})


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
    device: DeviceOption = None,
    interactive: Annotated[
        bool,
        typer.Option(
            "--interactive/--no-interactive",
            help="Modo REPL con historial y streaming en vez de un solo turno",
        ),
    ] = True,
    disable_shell: Annotated[
        bool,
        typer.Option(
            "--disable-shell",
            help=(
                "Desactiva que el modelo proponga comandos de shell (marcador "
                "RUN:) en modo --interactive. Activo por defecto; siempre "
                "requiere confirmación manual por comando y pasa por un "
                "blocklist — nunca se ejecuta nada sin tu 's'."
            ),
        ),
    ] = False,
    disable_search: Annotated[
        bool,
        typer.Option(
            "--disable-search",
            help=(
                "Desactiva que el modelo busque en internet (marcador SEARCH:) "
                "en modo --interactive. Activo por defecto; es de solo lectura, "
                "no requiere confirmación manual."
            ),
        ),
    ] = False,
    agent: AgentOption = "jarvis",
) -> None:
    """Envía un mensaje a un modelo (REPL interactivo por defecto)."""
    persona = _load_persona(agent)
    resolved_device = _resolve_device(device)
    router = _build_router(resolved_device)
    device = resolved_device
    allow_shell = not disable_shell
    allow_search = not disable_search
    system = system_file.read_text(encoding="utf-8") if system_file else ""
    system = _apply_persona_to_system(persona, system)
    try:
        backend = router.get(model)
    except (ModelNotFoundError, BackendLoadError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if interactive:
        _run_interactive(
            backend,
            system,
            max_tokens,
            no_think,
            device,
            model,
            allow_shell,
            allow_search,
            persona,
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
    device: DeviceOption = None,
    agent: AgentOption = None,
) -> None:
    """Compara tok/s, tiempo total y respuesta completa entre uno o varios modelos."""
    persona = _load_persona(agent)
    device = _resolve_device(device)
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
