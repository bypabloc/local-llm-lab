---
name: run-benchmark
description: Corre el benchmark de eficiencia (tok/s, prefill, memoria) para uno o varios modelos configurados en local-llm-lab y resume resultados. Usar cuando el usuario pida "benchmarkear", "comparar modelos", "cuál es más rápido", "medir eficiencia".
---

# Correr benchmark de modelos

1. Confirmar qué modelos comparar (por defecto: todos los que estén
   descargados en `models/` y configurados en `config/models.toml`).
2. Confirmar el prompt/system-file a usar — si el objetivo es medir el caso
   de uso real (AGENTS.md largo), usar un archivo representativo de tamaño
   similar, no un prompt trivial de una línea.
3. Ejecutar:
   ```bash
   uv run llm-lab bench --model <nombre1> --model <nombre2> \
       --system-file AGENTS.md --prompt "resumime esto en 3 puntos"
   ```
4. El comando reporta por modelo: tok/s de generación, tiempo de prefill,
   tokens totales de contexto usados, memoria RSS pico si está disponible.
5. Comparar contra los umbrales de `.claude/rules/research-context.md`
   (fluido >10-15 tok/s, aceptable 5-10, lento <5) al presentar resultados
   al usuario — no solo tirar la tabla cruda, interpretarla.
6. Guardar el output crudo en `tmp/bench-<fecha>.json` si el usuario quiere
   comparar corridas en el tiempo (el CLI soporta `--output tmp/...`).

No relanzar investigación web para esto — el benchmark es empírico sobre el
hardware real del usuario, más confiable que cifras de terceros para decidir
qué modelo usar en su máquina específica.
