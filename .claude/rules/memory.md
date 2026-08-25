# Memoria persistente del chat (`REMEMBER:`)

Contexto de por qué existe y cómo está diseñada — leer antes de tocar
`src/local_llm_lab/memory/`.

## Por qué existe

El usuario pidió que el chat interactivo recuerde preferencias/hechos que
comparte ("soy de tal forma", "me gusta que me escribas así") entre
sesiones, y que ante preguntas tipo "¿cuál es mi IP?" primero busque en esa
memoria antes de usar una tool. Se investigaron soluciones existentes
(Engram, Mem0, Zep) — todas terminan en el mismo patrón base para uso
local/ligero: SQLite + FTS5, sin grafo de nodos/relaciones tipadas. Se
replicó ese patrón dentro del proyecto en vez de depender de un binario
externo (Engram es un binario Go que se habla por MCP, no una librería
Python).

## Decisión de diseño: por qué no es un grafo

Un grafo real (`sujeto -[relación]-> objeto`) requiere que el modelo emita
sintaxis estructurada consistente en cada `REMEMBER:`. La investigación ya
documentada en `use-cases-research.md` registra que modelos de 2-4B fallan
tool-calling/formatos complejos con frecuencia. Por eso `REMEMBER:` guarda
texto libre (una frase), y la búsqueda es full-text, no traversal de grafo.

## Decisión de diseño: por qué OR + prefijo + stopwords, no AND estricto

Primer intento: `AND` estricto entre palabras de la query. Falló en la
práctica — "¿cómo me llamo?" no comparte ninguna palabra literal con "el
usuario se llama Pablo" (conjugación distinta: llamo vs. llama). Se cambió a:

1. Filtrar stopwords en español (lista fija en `store.py`, sin librería NLP)
   antes de armar la query — evita que "en"/"el"/"que" matcheen cualquier
   documento.
2. Truncar cada palabra restante a un prefijo de 4 caracteres y usar
   matching por prefijo de FTS5 (`llam*`) — cubre variaciones de
   conjugación simples sin un stemmer real.
3. Unir con `OR`, no `AND` — maximiza recall porque la pregunta del usuario
   rara vez repite el vocabulario exacto del hecho guardado.

Ver `tests/unit/test_memory_store.py` — el test
`test_search_encuentra_hecho_con_pregunta_que_no_comparte_palabras_clave`
es la garantía de que este caso no se rompe de nuevo.

## Decisión de diseño: deduplicación exacta, no difusa

El modelo a veces re-emite `REMEMBER:` con un hecho ya guardado en vez de
usar el bloque de recall (comportamiento observado en la práctica con
gemma4-e2b). `MemoryStore.save` deduplica por contenido normalizado
(lowercase + espacios colapsados) contra una tabla auxiliar
`memory_dedup` — FTS5 no soporta `UNIQUE` directamente. Se descartó
similitud difusa (embeddings/fuzzy matching) por ahora: agrega
complejidad y una dependencia nueva para un problema que la
deduplicación exacta ya resuelve en la práctica, dado que el modelo
tiende a repetir la misma frase casi literal, no a parafrasear.

## Decisión de diseño: instrucciones de tools en inglés

Los 4 archivos de `config/tools/*.md` (memory, search, shell, weather)
están en inglés, no español. Investigación previa (arXiv, comparativas de
prompt language) muestra un gap de 2-10% en instruction-following cuando
el prompt del sistema está en un idioma no-inglés, y que la mayoría de los
modelos open-source (Gemma, Qwen) se entrenan con más datos de instrucción
en inglés que en cualquier otro idioma — el propio texto del usuario
(lo que se guarda como hecho, y las respuestas de jarvis) se queda en
español, el cambio es solo en el instructivo del sistema. Se aplicó
también a la lista de tool names inline en `cli/main.py`
(`_run_interactive`) y al mensaje de recall (`_recall_relevant_memories`),
ya que ambos son parte del mismo contrato de instrucción que `memory.md`
referencia explícitamente ("you already know this about the user").

Estructura del prompt (misma en los 4 archivos, patrón de Mem0/Qwen/Gemma
cookbook): ROLE + GOAL + reglas explícitas de cuándo SÍ y cuándo NO usar la
tool (NOOP explícito, no solo el caso positivo) + formato exacto + ejemplos
few-shot. La categoría NOOP explícita (inspirada en el router de
ADD/UPDATE/DELETE/NOOP de Mem0) fue el cambio más impactante en la
práctica: antes, preguntas como "¿cuál es mi IP?" a veces disparaban un
`REMEMBER:` espurio porque el prompt solo describía el caso positivo.

## Decisión de diseño: hechos autocontenidos, no fragmentados

Bug observado: el modelo guardaba "Pablo prefiere respuestas concisas" (sin
la palabra "llama"/"nombre") cuando el usuario decía "soy Pablo, me gusta
que me escribas conciso" — dos datos en un mensaje, guardados de forma
fragmentada o incompleta. Buscar después "¿cómo me llamo?" no encontraba
nada porque ninguna palabra de la query aparecía en el hecho guardado.

Se resolvió agregando una instrucción explícita en `memory.md`: cada hecho
debe incluir el detalle específico (nombre, preferencia) y "contener las
palabras reales que alguien buscaría después" — sin tocar el código de
`_recall_relevant_memories` ni el matching de `store.py`. Verificado
end-to-end (3 corridas con `--no-think`, determinístico): el modelo pasó a
guardar "El usuario se llama Pablo y prefiere respuestas concisas" como un
único hecho autocontenido, y el recall de "¿cómo me llamo?" empezó a
funcionar sin más cambios. La lección: cuando el recall falla, revisar
primero si el problema es lo que se guardó (prompt) antes de asumir que
hace falta más lógica de búsqueda (código).

## Flujo completo

1. En modo `--interactive` (siempre activo, no hay flag para desactivarlo —
   es solo lectura/escritura local, bajo riesgo), antes de cada turno del
   usuario se busca en memoria con su texto de entrada
   (`_recall_relevant_memories`). Si hay resultados, se inyectan como
   mensaje `role: system` — el modelo los ve pero el usuario no, salvo que
   la respuesta los use.
2. Si la respuesta del modelo contiene una línea `REMEMBER: <hecho>`, se
   persiste (`_handle_remember_note`) y se le informa al modelo el
   resultado, igual que el resto de marcadores (`RUN:`, `SEARCH:`, etc.).

## Dónde vive la base de datos

`data/memory.db` en la raíz del repo (gitignoreada, patrón `data/*.db`),
calculada relativa a `cli/main.py` vía `_REPO_ROOT` — mismo mecanismo que
el fix de import de `devtools/searxng`, para no depender del cwd desde el
que se invoque el entry point instalado.

## Extender esto en el futuro

Si el volumen de hechos guardados crece mucho y el full-text simple deja de
alcanzar (falsos positivos/negativos frecuentes), la siguiente escalada
natural es embeddings locales (otro modelo `.gguf` de embeddings cargado en
paralelo), no un grafo — seguir la investigación de `use-cases-research.md`
antes de decidir.
