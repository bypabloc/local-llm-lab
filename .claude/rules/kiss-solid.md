# KISS y SOLID en este proyecto

Reglas concretas, no teoría. Cada punto tiene el porqué aplicado al router
de LLMs de este repo.

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
