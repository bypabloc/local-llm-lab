# Ejecución de comandos de shell desde el chat (`--allow-shell`)

Contexto de por qué existe esta feature y cómo está protegida — leer antes
de tocar `src/core/shell/` o el flujo `--allow-shell` en el CLI.

## Por qué existe

El usuario preguntó si el chat interactivo podía ejecutar comandos. La
respuesta original era no — el modelo solo generaba texto, sin ningún
mecanismo conectado a un shell real. Se agregó como feature explícita, opt-in
(`--allow-shell`, deshabilitado por defecto).

## Decisión de diseño: por qué NO tool-calling nativo

Los modelos configurados en este proyecto son 2-4B (gemma4-e2b) y hasta 8B
(qwen3-8b). La investigación ya documentada en `use-cases-research.md`
registra que el tool-calling nativo de modelos 8B es poco fiable en la
comunidad ("requieren más trabajo para alternar entre usar herramientas y
responder directamente, el modelo se rompe"). Con modelos aún más chicos
(2-4B) el riesgo es mayor. Por eso se usa un mecanismo de texto simple:
el modelo escribe una línea `RUN: <comando>` en su respuesta, y el CLI la
detecta con una regex — no se depende de la API de function-calling de
llama.cpp.

## Decisión de diseño: por qué ejecución con confirmación, no automática

El usuario pidió inicialmente ejecución automática sin confirmar. Se le
señaló el riesgo concreto (modelo 2-4B mucho más propenso a alucinar un
comando destructivo que Claude/GPT-4, sin revisión humana antes de que
corra) y decidió confirmación manual (s/n) + blocklist como doble capa. Este
es el comportamiento actual — **no cambiar a ejecución automática sin
volver a confirmar explícitamente con el usuario**, dado que fue una
decisión de seguridad deliberada, no un default arbitrario.

## Las dos capas de protección (ninguna es saltable por la otra)

1. **Blocklist** (`src/core/shell/blocklist.py`) — se evalúa
   *antes* de pedir confirmación. Si el comando matchea, se bloquea sin
   preguntar nada, sin importar qué responda el usuario después. Ver el test
   `test_run_with_confirmation_bloquea_comando_peligroso_aunque_confirm_sea_true`
   en `tests/unit/test_shell_runner.py` — es la garantía de que esto no se
   puede regresar por accidente.
2. **Confirmación manual** (`typer.confirm`, default `No`) — solo se
   pregunta si el comando pasó el blocklist. El usuario ve el comando exacto
   antes de decidir.

El blocklist revisa el comando completo **y** cada sub-comando de una
cadena (`&&`, `;`, `|`) por separado, para que un comando peligroso no se
cuele escondido detrás de uno inocuo (ej. `ls; rm -rf /`).

## Qué cubre el blocklist hoy

Categorías: `rm` recursivo/forzado o apuntando a raíz/home/cwd, `dd`,
formateo/particionado de disco, redirección a `/dev/`, fork bombs,
escalación de privilegios (`sudo`/`su`/`doas`), `chmod 777`, `chown -R`,
pipe de descarga directo a un shell (`curl ... | sh`), listeners de red,
`git push --force`/`reset --hard`/`clean -f`, desinstalación de paquetes del
sistema, escritura sobre directorios del sistema (`/etc/`, `/boot/`,
`/sys/`), `killall`/`pkill` sin filtro específico.

Ver `tests/unit/test_blocklist.py` para la lista exhaustiva de casos
bloqueados y permitidos — es la fuente de verdad, más confiable que este
resumen si hay dudas sobre un caso límite.

Agregar un patrón nuevo al blocklist: una entrada más en
`_BLOCKED_PATTERNS` (regex, motivo) — no requiere tocar lógica. Agregar el
caso correspondiente a `test_blocklist.py` en la misma modificación (TDD).

## Cómo se ejecuta lo que pasa el blocklist

`subprocess.run` con lista de argumentos (`shlex.split`), **nunca**
`shell=True` — evita una clase entera de inyección adicional más allá del
blocklist. Timeout de 30s por defecto.

## Flujo completo

1. Con `--allow-shell`, se agrega `SYSTEM_PROMPT_SUFFIX` al system prompt,
   instruyendo al modelo sobre el formato `RUN: <comando>`.
2. Tras cada respuesta del modelo, `extract_run_command` busca la última
   línea `RUN:` en el texto.
3. Si hay comando: se muestra, se corre el blocklist, se pide confirmación
   si pasó, se ejecuta si se confirmó.
4. El resultado (stdout/stderr/bloqueo/cancelación) se inyecta de vuelta al
   historial como mensaje `role: system`, para que el modelo lo vea en el
   siguiente turno y no asuma que el comando corrió si no corrió.

## Extender esto en el futuro

Si se agrega ejecución automática sin confirmar como opción (no el
default), debe ser un flag explícito y distinto de `--allow-shell` (ej.
`--allow-shell --yolo` o similar), nunca el comportamiento por defecto de
`--allow-shell`. El blocklist sigue aplicando siempre, sin excepción, en
cualquier modo.
