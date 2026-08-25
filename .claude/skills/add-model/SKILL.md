---
name: add-model
description: Agrega un modelo GGUF nuevo al router de local-llm-lab (entrada en config/models.toml, validación de path, opcionalmente descarga desde Hugging Face). Usar cuando el usuario pida "agregar modelo", "sumar un LLM nuevo", "probar tal modelo".
---

# Agregar un modelo nuevo

1. Confirmar con el usuario: nombre lógico del modelo (kebab-case, ej.
   `qwen3-8b`), repo de Hugging Face y archivo GGUF exacto, cuantización.
2. Verificar que el modelo respete las reglas de `.claude/rules/research-context.md`:
   licencia permisiva (Apache 2.0 / MIT preferido), tamaño razonable para
   CPU (~2-9GB en Q4), contexto declarado.
3. Agregar entrada en `src/core/config/models.toml`:
   ```toml
   [models.<nombre-logico>]
   path = "models/<archivo>.gguf"
   n_ctx = <contexto>
   n_threads = 8
   n_gpu_layers = 0
   ```
4. Si el usuario pide descargar el archivo, usar `huggingface-cli download`
   o indicar el comando — nunca hardcodear URLs de descarga en código Python,
   eso es un paso manual/documentado, no parte del router.
5. Correr `uv run llm-lab list` para confirmar que el router lo reconoce.
6. Si hay tests de integración relevantes, correrlos:
   `uv run pytest tests/integration -k <nombre-logico>`.

No se toca ningún archivo `.py` del router para este flujo — si hace falta
tocar código Python para "agregar un modelo", eso es una señal de que el
diseño violó KISS/OCP (ver `.claude/rules/kiss-solid.md`).
