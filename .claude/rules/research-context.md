# Contexto de investigación — modelos y hardware

Resumen de la investigación previa que originó este proyecto. Sirve como
contexto para decisiones de diseño (qué modelos soporta el config por
defecto, qué métricas mide el benchmark, qué umbrales se consideran
"fluido" vs "lento").

## Caso de uso objetivo

Chat general / asistente de tareas sencillas (no coding avanzado, no
razonamiento extendido). Contexto moderado: system prompt tipo AGENTS.md
más algunos archivos adicionales, no ventanas gigantes de 128K+.

## Hardware de referencia del usuario

Laptop sin GPU dedicada, 32GB+ RAM, solo CPU. Presupuesto de hardware
descartado tras investigación: con ese setup, no hay upgrade de <$500 que
mejore la experiencia sobre quedarse en CPU con un modelo de 3-4B (ver
sección "Conclusión sobre hardware").

## Modelos candidatos (verificados, con licencia permisiva real)

| Modelo | Tamaño Q4_K_M | RAM | Contexto | Licencia | Tok/s CPU medido |
|---|---|---|---|---|---|
| Qwen3-4B-Instruct-2507-GGUF | ~2.5GB | 4-6GB | 32K (128K YaRN) | Apache 2.0 | 12-15 tok/s (8-12 cores) — estimado por analogía, sin medición directa propia |
| Qwen3-8B-GGUF | ~5GB | 6-8GB | 32K (128K YaRN) | Apache 2.0 | 6-10 tok/s estimado en CPU pura (medido en GPU: 42 tok/s en RTX 3060) |
| Phi-4-mini-instruct-GGUF | ~2.2-2.5GB | 4-5GB | 128K real | MIT | 12 tok/s medido (Intel i7-12700, 12 cores) |
| Gemma-4-E2B-GGUF | ~4GB | 4GB | 128K | Apache 2.0 | 15 tok/s medido (CPU genérico) |
| Gemma-4-E4B-GGUF | ~5.5-6GB | 6-8GB | 128K | Apache 2.0 | 7.8 tok/s medido (Ryzen 5, 16GB) |
| Qwen2.5-14B-Instruct-GGUF | ~8.7GB | 10-12GB | 32K | Apache 2.0 | 4-5 tok/s medido — lento en CPU pura, no recomendado para chat interactivo |

Notas:
- Evitar Mistral-7B-Instruct-v0.3 en formato GGUF: la sliding-window
  attention está mal soportada en llama.cpp y el contexto real cae muy por
  debajo de lo anunciado (32K anunciado, ~4-8K real). Si se quiere Mistral,
  usar `transformers` puro, no GGUF.
- Preferir variantes con licencia Apache 2.0 o MIT sobre Llama Community
  License (que tiene cláusulas de escala/atribución) cuando la calidad es
  comparable.
- El **prefill** (procesar el system prompt/AGENTS.md) es compute-bound y
  escala con más cores; la **generación** token a token es
  memory-bandwidth-bound y no mejora mucho con más cores una vez pasado un
  umbral. Esto es relevante para medir "tiempo hasta primer token" además
  de tok/s de generación en el benchmark de este proyecto.

## Umbrales de "fluido" vs "lento" (para el benchmark)

- **Fluido / conversacional**: > 10-15 tok/s (por encima de velocidad de lectura humana)
- **Aceptable pero notorio**: 5-10 tok/s
- **Frustrante / no interactivo**: < 5 tok/s

## Conclusión sobre hardware (por qué no hay perfil de "GPU barata" en este proyecto)

Con presupuesto ≤$500 y punto de partida "laptop sin GPU dedicada": no hay
upgrade de esa laptop en sí (RAM extra no acelera tok/s una vez que el
modelo cabe, solo evita swap; eGPU requiere Thunderbolt/USB4 y ya excede el
presupuesto solo en el enclosure). La única vía de mejora real (GPU usada
tipo RTX 3060 12GB, ~$220-260) requiere una máquina de escritorio aparte,
fuera del alcance asumido de este proyecto. Por eso el backend por defecto
asume **CPU-only** (`n_gpu_layers=0`), con soporte opcional a GPU vía config
si en el futuro el usuario corre esto en otra máquina.

## Cómo se traduce esto al diseño del proyecto

1. El config por defecto (`config/models.toml`) trae Qwen3-4B, Qwen3-8B,
   Phi-4-mini y Gemma-4-E2B como entradas — no se asume que el usuario
   tenga los `.gguf` descargados, pero la config ya sabe dónde deberían
   estar y con qué parámetros cargarlos.
2. El benchmark mide tok/s de generación Y tiempo de prefill por separado,
   porque el caso de uso (AGENTS.md largo) hace que el prefill importe tanto
   como la generación.
3. El comando `bench` compara varios modelos en una sola corrida para que
   decidir "cuál me conviene" sea empírico sobre el hardware real, no solo
   basado en benchmarks de terceros.
