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
