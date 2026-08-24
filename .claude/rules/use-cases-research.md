# Casos de uso reales de LLMs locales — investigación de comunidad

Resumen de investigación (r/LocalLLaMA, Hacker News, The Register, proyectos
de GitHub activos) sobre para qué usa la gente en la práctica los LLMs open
source livianos ejecutados en local — no benchmarks, uso real reportado.
Sirve de contexto para decidir qué construir después en este proyecto (ej.
si vale la pena un modo `serve` para integrarlo con un editor).

## Categorías con evidencia real, ordenadas por solidez de la evidencia

1. **Coding — la más documentada.** Patrón dominante: Continue.dev + Ollama/
   llama.cpp + Qwen2.5/3-Coder para autocompletado en VS Code. Georgi
   Gerganov (creador de llama.cpp) usa asistencia de código local a diario.
   Bueno para autocompletado y explicar código; débil para generación
   multi-archivo compleja.
2. **Uso offline / viaje.** El encaje más natural para 4-8B: no compite
   contra nada mientras no hay internet. Caso citado: alguien redactó un
   post de blog completo en un vuelo con Llama 3.1 8B.
3. **Privacidad como filtro duro.** Empresa alemana (Makandra) migró a
   local por GDPR. Motivación repetida: desconfianza en retención de datos
   de proveedores cloud. Contrapunto honesto: el fundador de Nomic dice que
   su propia empresa usa OpenAI con zero-retention en vez de modelos
   locales, porque &lt;20B "no alcanza" para trabajo empresarial serio.
4. **Automatización de tareas triviales de alto volumen**: mensajes de
   commit, clasificación de emails, extracción de PDFs a JSON. Lógica:
   "gratis y suficientemente bueno" gana a "mejor pero cobra por token"
   cuando el volumen es alto y la tarea es simple.
5. **RAG personal / "second brain"** (Obsidian + Copilot/Smart Connections
   sobre Ollama). Ecosistema maduro, pero con un dato honesto: RAG casero
   sin optimización cae por debajo de 50% de precisión.
6. **Roleplay/creative writing** (SillyTavern). Comunidad grande, pero
   prefiere modelos 12B+ para "personalidad" — 4-8B es el piso funcional,
   no el punto dulce.
7. **Integraciones caseras** (Home-LLM para Home Assistant, bots de
   Telegram/Discord). Nicho pero con proyectos mantenidos en el tiempo.

## Frustraciones reportadas repetidamente (para expectativas honestas)

- Modelos &lt;20B siguen por detrás de la frontera cloud actual (la brecha
  se cierra, pero sigue existiendo).
- Necesitan prompts más precisos y estructurados que Claude/GPT — toleran
  peor el contexto desordenado.
- Tool calling complejo es poco fiable en 8B.
- Cuantización a veces rompe funcionalidad, no solo reduce velocidad
  (contexto efectivo menor al nominal anunciado).
- Ventana de contexto "goldfish-sized" en la práctica: techo útil real
  reportado de ~2000-3000 líneas de código, muy por debajo de la ficha
  técnica.
- CPU-only es demasiado lento para uso diario serio (0.5-3 tok/s sin GPU)
  — consistente con lo medido en este proyecto (ver benchmarks en
  `research-context.md` y las corridas en `tmp/bench-*.json`).

## Recomendaciones aplicadas a este proyecto y este hardware

Hardware de referencia: RTX 4060 Laptop 8GB VRAM, 18 cores, 32GB RAM.
Medido en este repo: GPU da 3-7.5x sobre CPU, todos los modelos configurados
quedan en "fluido" con `--device gpu` (ver `tmp/bench-*-gpu.json`).

1. **Autocompletado de código en editor — mejor ROI.** Requiere un modo
   `serve` (servidor HTTP compatible con API de OpenAI, ej.
   `llama_cpp.server`) para que Continue.dev u otro cliente le pegue
   directo, reusando `models.toml` y el flag `--device` ya existentes. No
   implementado todavía — candidato natural de próxima feature.
2. **Reemplazar llamadas triviales de alto volumen a APIs pagas**: commits,
   clasificación de texto, resúmenes cortos. Gemma-4-E2B (el más rápido en
   este hardware, ~87 tok/s en GPU) es el candidato natural.
3. **Modo offline/viaje** como respaldo real con Qwen3-4B/8B ya descargado
   y probado.
4. **Evitar por ahora**: RAG sobre notas personales sin invertir en tunear
   el retrieval; tool calling/agentes complejos encadenados; cualquier tarea
   donde ya se usa Claude/GPT y la calidad importa — no hay evidencia de que
   reemplazarlo con 4-8B local salga bien.

## Cómo usar esto en decisiones futuras del proyecto

Si se agrega una feature nueva a este router, evaluar contra esta lista:
¿encaja en una categoría con evidencia real (coding, offline, tareas
triviales de alto volumen) o en una de las que la comunidad reporta como
débil (RAG sin tuning, tool calling complejo)? Preferir invertir esfuerzo en
lo primero.
