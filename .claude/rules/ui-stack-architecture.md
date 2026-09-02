# Arquitectura del stack de UI: Tauri v2 + React 19 + Django

Contexto de por qué existe esta parte del repo, cómo está estructurada y
qué invariantes hay que preservar al tocarla — leer antes de modificar
`ui/`, `src-tauri/` o `server/`.

## Por qué existe

El proyecto empezó como CLI Typer puro (`llm-lab chat/bench/list`). El
usuario pidió una UI de escritorio multiplataforma (Windows/Linux/Mac) con
un chat visual que soportara los mismos parámetros que el CLI. La
investigación de opciones (Tauri, Electron, pywebview, Flutter, .NET MAUI)
concluyó en **Tauri v2 + React 19**: bundles 20-50x más chicos que Electron,
menor RAM, y adopción en alza en 2025-2026. El backend no se reescribió en
Rust ni en JS — se mantiene Python/Django como servidor HTTP local,
lanzado por Tauri como **sidecar** (proceso hijo empaquetado con
PyInstaller), comunicado por HTTP a un puerto efímero.

## Decisión de diseño: por qué no se movió `src/core/`

`src/core/` (router, backends, memory, shell, personalities, config,
benchmark) es Python puro, sin acoplamiento a Typer salvo `cli/main.py`.
Se evaluó mover ese paquete dentro de `server/` para "que Django lo tenga
cerca" y se descartó: hubiera roto 20+ imports absolutos (`from core.xxx
import ...`), los tests existentes en `tests/unit/`+`tests/integration/`, y
el entry point `core.cli.main:app` — sin ningún beneficio real, porque
Django no exige que sus dependencias vivan bajo su propio árbol.

En su lugar, el repo se convirtió en **uv workspace**: `pyproject.toml` raíz
declara `[tool.uv.workspace] members = ["server"]`, y `server/pyproject.toml`
depende de `local-llm-lab` (el paquete `core`) vía `[tool.uv.sources]
local-llm-lab = { workspace = true }`. Un solo `.venv` en la raíz sirve a
ambos paquetes.

**Comando obligatorio para sincronizar dependencias**: `uv sync
--all-packages`. El `uv sync` normal (sin `--all-packages`) NO instala
`server/` — es la causa más probable si falta Django/daphne/pytest-django
en el venv después de un `git pull`.

`cli/main.py` (633 líneas, acoplado a `typer.echo`/`typer.confirm`/
`typer.prompt`) **no se reusó tal cual** — se reimplementó como servicios
Django puros en `server/llm/services/`, replicando el comportamiento
exacto (mismo orden de detección de marcadores, mismo armado de system
prompt) pero sin dependencia de terminal. El CLI original **sigue
existiendo y sigue funcionando** — no se eliminó, sirve para debug rápido
sin levantar Django.

## Estructura del mono-repo

```
local-llm-lab/
├── src/core/              # sin cambios — router, backends, memory, shell,
│                          # personalities, config, benchmark, cli (Typer)
├── tests/                 # tests de src/core/, sin cambios
├── ui/                    # React 19 + Vite + TypeScript estricto
│   ├── src/
│   │   ├── api/            # client.ts (fetch + SSE), types.ts (espejo de payloads Django)
│   │   ├── components/     # Sidebar, ChatPanel, MessageBubble, RunConfirmCard, BenchView
│   │   ├── hooks/           # useChatStream (orquesta el streaming), useModels
│   │   ├── App.tsx, main.tsx
│   └── e2e/                # tests Playwright, contra el backend Django REAL, sin mocks
├── src-tauri/             # shell nativo Rust — nombre convencional Tauri v2 (no "src/")
│   ├── binaries/            # sidecar PyInstaller, GITIGNOREADO — se genera con build_sidecar.sh
│   ├── capabilities/        # permisos Tauri v2 (allow-list explícito, sin allowlist global)
│   ├── src/lib.rs           # lanza el sidecar, health-check, expone get_server_port
│   └── tauri.conf.json
├── server/                # Django — reemplaza cli/main.py como orquestador HTTP
│   ├── manage.py
│   ├── server/              # settings.py, urls.py, asgi.py
│   ├── llm/                 # app Django
│   │   ├── services/         # system_prompt.py, device.py, router_singleton.py,
│   │   │                     # chat_turn.py, shell_confirm.py — lógica pura, testeada con FakeBackend
│   │   ├── views.py          # vistas HTTP delgadas: parsean request, llaman al servicio, serializan
│   │   └── tests/            # pytest + pytest-django + pytest-asyncio
│   ├── run_sidecar.py       # entrypoint del sidecar — NO usar manage.py runserver (trae autoreload)
│   ├── server.spec          # PyInstaller
│   └── build_sidecar.sh     # compila con PyInstaller y copia a src-tauri/binaries/
├── pnpm-workspace.yaml     # packages: ["ui"]
└── package.json            # raíz, scripts pnpm
```

## Contrato HTTP entre `ui/` y `server/`

- `GET /api/models` — lista `models.toml` resuelta.
- `POST /api/chat` — **SSE** (Server-Sent Events), no WebSocket. Body:
  `{model, device, agent, max_tokens, no_think, allow_shell, allow_search,
  system_file_content, history[]}`. `history[]` viaja completo en cada
  request — el server es stateless salvo el router/backend cacheados
  (`router_singleton.py`). Eventos emitidos: `token`, `run_proposed`,
  `tool_result`, `assistant_done`.
- `POST /api/shell/confirm` — segundo paso del flujo RUN: (ver abajo).
- `POST /api/bench` — igual que `llm-lab bench`, mismo payload de salida
  (`tokens_per_second, total_seconds, prefill_seconds, ...`).

**Por qué SSE y no WebSocket**: el chat es turno-a-turno (request → stream
de respuesta → fin), nunca necesita push del server sin que el cliente
pida antes. WebSocket hubiera exigido Django Channels + un server ASGI con
soporte websocket — infraestructura extra sin beneficio real. Decisión
tomada explícitamente con el usuario, no reabrir sin motivo nuevo.

## Decisión de diseño: el flujo de confirmación de RUN: es de dos requests HTTP

En el CLI, `typer.confirm()` bloquea el proceso hasta que el usuario
responde s/n en la misma terminal — no hay problema de estado porque todo
pasa en el mismo turno síncrono. En HTTP eso no es posible: no se puede
dejar una request colgada esperando un clic del usuario en el navegador.

Por eso `run_chat_turn` (`server/llm/services/chat_turn.py`) **corta el
stream** en cuanto detecta `RUN:` — emite `run_proposed` y no evalúa el
resto de marcadores ni dispara la ronda de seguimiento en esa misma
llamada. El frontend:

1. Recibe `run_proposed`, muestra `RunConfirmCard` con Ejecutar/Rechazar.
2. Si el usuario aprueba: `POST /api/shell/confirm` (que solo llama
   `run_with_confirmation(command, confirm=True)` — el blocklist de
   `core/shell/blocklist.py` sigue aplicando del lado server, defensa en
   profundidad aunque la UI ya lo muestre bloqueado).
3. El frontend agrega el resultado como mensaje `role: system` al
   `history[]` local y reabre un **segundo** `POST /api/chat` con ese
   historial actualizado — reproduciendo la ronda de seguimiento que en el
   CLI ocurre automáticamente dentro del mismo turno.

Si se toca este flujo, mantener el orden de detección de marcadores en
`chat_turn.py` — **RUN (si allow_shell) → SEARCH (si allow_search) → IP →
LOCATION → WEATHER → REMEMBER** — idéntico a `core/cli/main.py`. Un test
específico (`test_orden_de_deteccion_run_antes_que_search`) blinda esto.

## Decisión de diseño: singleton de router en memoria de proceso

`LLMRouter.get()` cachea backends indefinidamente (carga eager del GGUF en
el constructor, costosa). `server/llm/services/router_singleton.py`
mantiene un `LLMRouter` por `device` (`cpu`/`gpu`) en un dict
módulo-level, protegido con `threading.Lock`. Efectos a tener en cuenta:

- El dev server de Django con autoreload (`manage.py runserver`)
  reinstancia el módulo en cada guardado de archivo, perdiendo el cache
  (recarga el modelo, lento). Correr `--noreload` mientras se itera sobre
  `chat_turn.py`/`views.py`, o levantar el server directo con `daphne`
  (ver comandos abajo) en vez de `runserver`.
- En el sidecar empaquetado no aplica (sin autoreload).
- `router.unload(name)` libera VRAM/RAM — solo se llama explícitamente en
  `/api/bench` entre modelos (igual que hacía `llm-lab bench`). El chat no
  descarga modelos entre turnos.

## Decisión de diseño: `MemoryStore` (SQLite) se crea por request, no se comparte entre threads

`run_chat_turn` corre síncrono dentro de un `loop.run_in_executor` en la
vista SSE async (`server/llm/views.py`). `sqlite3` no tolera una conexión
usada desde un thread distinto al que la abrió. Por eso `MemoryStore(
memory_db_path)` se instancia **dentro** de la función `produce()` que
corre en el executor, no antes en el hilo async — bug real encontrado y
corregido durante la implementación (ver commit), cubrir con cuidado si se
toca ese flujo.

`data/memory.db` es el **mismo archivo** que usa el CLI — no hay dos
bases. Un `REMEMBER:` guardado desde la UI es recuperable desde el CLI y
viceversa (verificado manualmente, ver sección de verificación end-to-end
más abajo).

## Decisión de diseño: `.env` se carga explícitamente en `settings.py`

Bug real encontrado: Django nunca cargaba `.env` (a diferencia del CLI,
que lo hace explícito en `cli/main.py:36`), así que `TAVILY_API_KEY`/
`SEARXNG_URL`/`SEARCH_PROVIDER` no llegaban al proceso salvo que ya
estuvieran en el entorno del shell que lanza `daphne`. `settings.py` ahora
llama `load_dotenv(REPO_ROOT / ".env")` (reusa `core.config.dotenv`,
misma función que usa el CLI) antes de leer cualquier env var. Si SEARCH
deja de funcionar desde la UI, este es el primer lugar a revisar.

## Decisión de diseño: `LLM_LAB_PROJECT_ROOT` para el sidecar empaquetado

`core/config/models.py::load_model_configs()` resuelve la raíz del repo
subiendo 4 niveles desde `__file__` — funciona en dev, pero dentro de un
binario PyInstaller congelado `__file__` apunta a la carpeta temporal
`_MEI.../core/config/models.py`, no al checkout real. Bug real encontrado:
el sidecar buscaba los `.gguf` en `/tmp/models/...` en vez de la raíz del
repo.

Fix: `server/llm/services/device.py::resolve_project_root()` lee la env
var `LLM_LAB_PROJECT_ROOT` si está seteada (la pasa `src-tauri/src/lib.rs`
al lanzar el sidecar, calculada como el padre del cwd del proceso Tauri) y
la pasa como `project_root=` explícito a `load_model_configs()`. Si se
agrega un nuevo path relativo a la raíz del repo en el sidecar, pasar
siempre por este mecanismo, nunca asumir `__file__` funciona igual
empaquetado que en dev.

## Decisión de diseño: `AUTOBAHN_USE_NVX=0` obligatorio en el sidecar

`daphne` (servidor ASGI usado para servir SSE) importa `autobahn`
(soporte websocket, no usado por SSE pero sigue siendo una dependencia
transitiva). `autobahn.nvx` es una aceleración Cython que intenta
compilar C en runtime — no soportado dentro de un binario PyInstaller
congelado, rompe el arranque con `FileNotFoundError`. `server/
run_sidecar.py` setea `os.environ.setdefault("AUTOBAHN_USE_NVX", "0")`
**antes** de cualquier import de `daphne` (a nivel de módulo, no dentro de
`main()` — daphne se importa antes de que `main()` corra). Si se toca este
archivo, no mover esa línea después de los imports.

## Sidecar: cómo se construye y qué esperar

```bash
cd server
./build_sidecar.sh   # requiere rustc en PATH (para detectar el target triple)
```

Genera `src-tauri/binaries/llm-lab-server-<target-triple>` (ej.
`llm-lab-server-x86_64-unknown-linux-gnu`), ~500MB (CPU-only: incluye
`llama-cpp-python` con su `.so` nativo + todo Django/daphne empaquetado).
**MVP actual es CPU-only** — un sidecar con soporte CUDA es
significativamente más pesado y es una mejora futura documentada, no
bloqueante. `src-tauri/binaries/` está gitignoreado — cada quien
regenera el sidecar localmente, no se versiona el binario de 500MB.

`server.spec` (PyInstaller) usa `collect_all("llama_cpp")` y
`collect_data_files("core")` — necesario para que `models.toml` y los
`.md` de `personalities/`/`config/tools/` (leídos vía
`importlib.resources`) viajen dentro del bundle. Si se agrega un archivo
de datos nuevo a `core/` que se lee por `importlib.resources`, confirmar
que sigue viajando en el sidecar tras un rebuild — no asumido
automáticamente por PyInstaller sin el `collect_data_files`.

## Prerequisitos de sistema (Tauri v2, Ubuntu/WSL2)

Rust (vía `rustup`, no `apt`) + librerías de sistema del webview
(`libwebkit2gtk-4.1-dev`, `libgtk-3-dev`, etc.). Comandos completos en el
README de `src-tauri/` o pedirlos de nuevo si hace falta reinstalar en una
máquina nueva — no se repiten aquí para no desincronizar con la versión
real de Tauri instalada.

**WSL2 específico**: Tauri necesita `$DISPLAY` seteado (WSLg). Si
`echo $DISPLAY` da vacío y `pnpm tauri dev`/el binario fallan con
`Failed to initialize gtk backend!`, revisar `C:\Users\<usuario>\.wslconfig`
— la clave `guiApplications=false` bajo `[wsl2]` desactiva WSLg
completamente. Ponerla en `true`, `wsl --shutdown` desde PowerShell, y
abrir una terminal completamente nueva (no alcanza con la misma pestaña
vieja) para que WSLg reinicie.

## KISS y SOLID aplicados a este stack (complementa `kiss-solid.md`)

- **Vistas Django delgadas, servicios gordos**: `views.py` solo parsea el
  request, llama a un servicio de `llm/services/`, y serializa la
  respuesta. Toda la lógica de negocio (armado de system prompt,
  orquestación de marcadores, resolución de device) vive en servicios
  puros, testeados sin HTTP de por medio (`FakeBackend`, sin Django test
  client). Esto es lo que permitió testear `chat_turn.py` con 12 casos
  unitarios sin levantar un server real.
- **Sin DRF por KISS**: la superficie HTTP es 4 endpoints simples. Django
  Rest Framework hubiera agregado serializers/viewsets para un beneficio
  marginal — `JsonResponse` + `json.loads(request.body)` a mano es
  suficiente y más fácil de seguir.
- **`history[]` completo en cada request, sin sesión server-side**: evita
  la complejidad de manejar estado de conversación entre requests (Redis,
  sesiones Django, etc.) — el cliente ya necesita el historial completo
  para renderizar la UI, así que reenviarlo es gratis y mantiene el
  server sin estado por conversación (solo cachea backends, no historial).
- **Un solo `useChatStream` hook, no una librería de estado**: no se
  introdujo Redux/Zustand para 4 piezas de estado (mensajes, streaming,
  RUN pendiente, tok/s). `useState`+`useRef` alcanza; escalar a una
  librería de estado el día que la complejidad real lo pida, no antes.
- **Tipos TS espejo manuales (`api/types.ts`), no generación automática
  desde el schema de Django**: 4 endpoints, payloads chicos y estables —
  generar tipos desde OpenAPI/schema hubiera sido una dependencia y un
  paso de build extra para un problema que copiar 5 interfaces resuelve
  en minutos. Reevaluar si el número de endpoints crece mucho.

## Verificación end-to-end obligatoria antes de dar por buena una task en este stack

No alcanza con `uv run pytest` + `tsc` verdes — hay cosas que solo un
modelo real o un clic real exponen (ver historial de bugs reales
encontrados así: closure impuro en `useChatStream` que Strict Mode
exponía, `.env` no cargado, paths rotos en el sidecar empaquetado). Antes
de cerrar una tarea que toque `ui/`, `server/` o `src-tauri/`:

1. `uv run pytest && uv run ruff check . && uv run mypy src server` — verde.
2. `pnpm --filter ui exec tsc -b && pnpm --filter ui run lint` — verde.
3. Levantar el server real (`daphne`, ver comandos) + `pnpm --filter ui
   dev`, y correr al menos un turno de chat contra un modelo GGUF real —
   no solo `FakeBackend`.
4. Si se tocó `useChatStream`/`chat_turn.py`/cualquier flujo de streaming:
   correr `pnpm --filter ui exec playwright test` contra el backend real
   (no mockeado) — es lo único que hubiera atrapado el bug del closure
   impuro, invisible en tests unitarios y en curl.
5. Si se tocó el sidecar/PyInstaller/Tauri: reconstruir (`build_sidecar.sh`
   + `cargo build` en `src-tauri/`) y probar el binario empaquetado
   directo, no asumir que "funciona en dev = funciona empaquetado" (dos
   bugs reales — `AUTOBAHN_USE_NVX`, `LLM_LAB_PROJECT_ROOT` — solo
   aparecían en el binario congelado).

## Comandos de este stack

```bash
# Instalar todo (Python workspace + Node)
uv sync --all-packages
pnpm install

# Server Django solo (dev, sin autoreload para no perder el cache de modelos)
PYTHONPATH="src:server" uv run daphne -b 127.0.0.1 -p 8000 server.asgi:application

# Frontend solo
pnpm --filter ui dev

# App Tauri completa (lanza Vite + sidecar automáticamente)
source "$HOME/.cargo/env"   # si rustc no está en el PATH de la sesión
pnpm tauri dev

# Tests
uv run pytest                              # core + server, todo el workspace Python
pnpm --filter ui exec tsc -b                # typecheck frontend
pnpm --filter ui run lint                   # oxlint
pnpm --filter ui exec playwright test       # e2e contra backend real (requiere server + vite corriendo o webServer de playwright.config.ts los levanta)

# Sidecar (regenerar tras tocar server/ o src/core/)
cd server && ./build_sidecar.sh

# Build de la app instalable (genera .deb/.AppImage/.exe/etc. según plataforma)
pnpm tauri build
```

## Extender esto en el futuro

Si se agrega persistencia de conversaciones (hoy vive solo en
`localStorage` del navegador, se pierde al cerrar), evaluar primero si
`data/memory.db` (ya compartido con el CLI) puede extenderse con una tabla
nueva antes de introducir una base de datos Django real — mismo principio
de "no agregar infraestructura antes de que la necesidad sea concreta" que
ya aplica el resto del proyecto (ver `kiss-solid.md`).

Si se agrega soporte GPU/CUDA al sidecar empaquetado, documentar acá cómo
se distingue el build CPU vs GPU (probablemente dos sidecars con sufijo
distinto, o un flag de `build_sidecar.sh`) — no está resuelto todavía.
