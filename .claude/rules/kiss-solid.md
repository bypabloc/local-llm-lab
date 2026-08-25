# KISS y SOLID en este proyecto

Reglas concretas, no teoría. Cada punto tiene el porqué aplicado al router
de LLMs de este repo. Desde que se agregó el stack de UI (Tauri v2 + React
19 + Django, ver `ui-stack-architecture.md`), estos mismos principios
aplican también ahí — sección dedicada más abajo.

## KISS

- **Un backend hoy = una interfaz simple, no una jerarquía especulativa.**
  Solo se soporta `llama-cpp-python`. La clase `LlamaCppBackend` no necesita
  una superclase abstracta `Backend` hasta que exista un segundo backend
  real con necesidad de intercambiarse en runtime. Cuando aparezca esa
  necesidad concreta, se extrae el protocolo — no antes.
- **Config en TOML plano, no un sistema de plugins.** `models.toml` es una
  lista de entradas con nombre, path, contexto y parámetros de carga. No se
  construye un sistema de "providers" o "loaders" registrables hasta que
  haya un caso real que lo pida.
- **El CLI no reimplementa un framework de benchmarking.** Mide tok/s y
  tiempo de prefill con `time.perf_counter()` y conteo de tokens del propio
  backend. No se integra un framework externo de profiling para esto.
- **Tres modelos similares en el config no son una razón para generar
  código.** Repetir tres bloques TOML es más simple que escribir un
  generador de config.

## SOLID (aplicado con criterio, no como checklist)

- **SRP real**: `router/` decide *qué* backend/modelo usar dado un nombre
  lógico. `backends/` sabe *cómo* hablar con llama-cpp-python. `benchmark/`
  sabe *cómo medir*. `cli/` solo parsea argumentos y orquesta las llamadas.
  Ninguna de estas capas conoce los detalles internos de la otra.
- **OCP con límite**: el router debe permitir agregar un modelo nuevo
  editando solo `models.toml`, sin tocar código Python. Pero esto no se
  extiende a "agregar un backend nuevo sin tocar código" — eso sí requiere
  código, porque hoy no hay necesidad real de un mecanismo de plugins.
- **DIP donde importa**: `router` depende de una interfaz mínima de backend
  (protocolo con `load()`, `generate()`, `count_tokens()`), no de la clase
  concreta `LlamaCppBackend` — esto permite testear el router con un fake
  backend en memoria, que es el motivo real (testabilidad), no "por si
  algún día cambiamos de librería".
- **ISP**: la interfaz de backend expone solo los métodos que el router y
  el benchmark realmente llaman. No se agregan métodos "por completitud" de
  lo que llama-cpp-python ofrece.

## Señal de que se está sobre-ingenierizando este proyecto

Si agregar un modelo nuevo requiere tocar más de un archivo TOML, algo se
rompió. Si agregar un backend nuevo (cuando eso pase) requiere tocar más de
2-3 archivos (la implementación + el registro en el router), algo se
rompió. Si un test necesita mockear más de una capa para probar una unidad,
la separación de responsabilidades no está bien puesta.

## KISS y SOLID en el stack de UI (`ui/`, `server/`, `src-tauri/`)

Detalle completo de las decisiones de arquitectura en
`ui-stack-architecture.md`. Resumen de KISS/SOLID aplicado ahí:

- **Vistas Django delgadas, servicios gordos (SRP)**: `server/llm/views.py`
  solo parsea request → llama a un servicio de `services/` → serializa.
  Ningún servicio conoce Django (`HttpRequest`, `JsonResponse`) — son
  funciones puras testeadas con `FakeBackend`, sin HTTP de por medio. Esto
  es lo mismo que ya hace `router/` vs `backends/` vs `cli/` en el core:
  separar "qué lógica corre" de "cómo llega el request".
- **Sin DRF, sin generación de tipos desde schema (KISS)**: 4 endpoints
  HTTP con payloads chicos y estables. `JsonResponse` a mano y tipos TS
  copiados manualmente en `ui/src/api/types.ts` son más simples de seguir
  que agregar serializers/viewsets de DRF o un generador OpenAPI para un
  problema que no lo justifica todavía. Reevaluar solo si el número de
  endpoints crece de forma real.
- **Sin librería de estado en React (KISS)**: `useChatStream` usa
  `useState`+`useRef` para las 4 piezas de estado del chat (mensajes,
  streaming, RUN pendiente, tok/s). No se introdujo Redux/Zustand/Jotai
  para eso — sería exactamente el mismo error que "agregar una interfaz
  Backend abstracta para un solo backend real".
- **`history[]` completo por request, sin sesión server-side (KISS)**: el
  cliente ya necesita el historial completo para renderizar; reenviarlo en
  cada `POST /api/chat` evita construir un mecanismo de sesión (Redis,
  Django sessions) para un problema que no existe todavía.
- **`router_singleton.py` reusa `LLMRouter` sin reimplementarlo (DIP/SRP)**:
  el server HTTP no reinventa el cacheo/carga de modelos — inyecta
  `LlamaCppBackend` en el mismo `LLMRouter` del core, solo le agrega un
  layer de locking para uso concurrente. Ningún código nuevo duplica lo
  que `router/llm_router.py` ya resuelve.
- **`ChatEvent` (Literal + payload dict) en vez de una jerarquía de clases
  de eventos (KISS)**: 4 tipos de evento (`token`, `run_proposed`,
  `tool_result`, `assistant_done`), todos serializables a JSON sin
  lógica propia — un dataclass con un `Literal` alcanza, no hace falta un
  patrón Visitor ni subclases por tipo de evento.

### Señal de sobre-ingeniería específica de este stack

Si un servicio de `server/llm/services/` necesita importar algo de
`django.*` para su lógica (no solo para el tipo de retorno de una vista),
la separación se rompió — la lógica de negocio no debería saber que corre
detrás de HTTP. Si agregar un endpoint nuevo requiere tocar más de
`views.py` + `urls.py` + un servicio nuevo, algo se está acoplando de más.
