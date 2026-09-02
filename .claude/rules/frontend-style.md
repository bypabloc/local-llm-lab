# Estilo TypeScript/React — `ui/`

Convenciones del frontend del stack de UI (`ui/`). Complementa
`.claude/rules/ui-stack-architecture.md` (arquitectura/decisiones) y las
reglas globales del usuario en `~/.claude/CLAUDE.md` (TS estricto, sin
`any`, sin comentarios de "qué hace" el código).

## Versión y tipado

- React **19**, TypeScript estricto (`strict: true`,
  `noImplicitAny: true`, `strictNullChecks: true` en
  `ui/tsconfig.app.json` — agregado explícitamente, Vite 8 no lo trae por
  defecto).
- `any` prohibido. Los dos puntos de interoperabilidad no tipada del
  proyecto (`window.__TAURI_INTERNALS__` para detectar si corre dentro de
  Tauri, y el resultado de `JSON.parse` del stream SSE) usan `unknown` +
  narrowing explícito, no `any`.
- `pnpm --filter ui exec tsc -b` sin errores es un requisito de cierre de
  cualquier cambio en `ui/`, no opcional.

## Package manager

- **pnpm exclusivamente** en todo el mono-repo — nunca `npm install` ni
  `yarn`. Decisión explícita del usuario, no reabrir sin motivo nuevo.
  `pnpm --filter ui <comando>` para correr algo solo en el paquete `ui`.

## Formato y lint

- `oxlint` (config default de Vite scaffold, `ui/.oxlintrc.json`) como
  linter — `pnpm --filter ui run lint` sin errores antes de cerrar una
  tarea.
- Sin punto y coma, sin configuración de Prettier custom — se respeta el
  estilo que ya sale del scaffold de Vite (comillas dobles, 2 espacios).

## Nomenclatura

```text
PascalCase.tsx        # componentes (Sidebar.tsx, ChatPanel.tsx)
useXxx.ts              # hooks — prefijo "use" obligatorio (useChatStream.ts, useModels.ts)
camelCase.ts           # módulos que no son componentes/hooks (client.ts, types.ts)
```

## Estructura de módulo

```text
ui/src/
├── api/          # client.ts (fetch + SSE contra el backend), types.ts (tipos espejo de los payloads Django)
├── components/   # un archivo por componente, sin index barrel
├── hooks/        # lógica con estado reusable, separada de los componentes que la consumen
```

- **`api/types.ts` debe reflejar exactamente los payloads que devuelve
  `server/llm/views.py`** — si un endpoint Django cambia su shape de
  respuesta, actualizar el tipo TS en el mismo cambio, no después. No hay
  generación automática desde el schema (ver `kiss-solid.md`, sección de
  este stack, por qué).
- Componentes reciben datos y callbacks por props tipadas explícitas
  (`interface Props { ... }`), nunca `React.FC` con props inline sin
  nombre.

## Estado y efectos — la regla que costó un bug real

**Nunca mutar una variable de closure dentro de un updater de
`setState`.** Bug real encontrado en `useChatStream.ts`: un `assistantId`
local se mutaba dentro de `setMessages((prev) => { assistantId = ...; ...
})` — funcionaba "por casualidad" en producción pero React Strict Mode
invoca los updaters dos veces en dev para detectar exactamente esta
impureza, y el mensaje del assistant nunca llegaba a renderizarse. El
backend funcionaba perfecto (confirmado con curl) — el bug era invisible
sin abrir la consola del browser o correr un test Playwright real.

Fix aplicado: el id vive en un `useRef` (`assistantIdRef.current`), leído
y escrito **fuera** del updater; el updater en sí solo usa una constante
ya capturada, puro.

```tsx
// ❌ mal — muta una variable de closure dentro del updater
let assistantId: string | null = null
setMessages((prev) => {
  if (assistantId === null) {
    assistantId = makeId()  // side-effect impuro, StrictMode lo expone
    return [...prev, { id: assistantId, ... }]
  }
  return prev.map((m) => m.id === assistantId ? { ... } : m)
})

// ✅ bien — el id vive en un ref, el updater es puro
const assistantIdRef = useRef<string | null>(null)
if (assistantIdRef.current === null) {
  const id = makeId()
  assistantIdRef.current = id
  setMessages((prev) => [...prev, { id, ... }])
} else {
  const id = assistantIdRef.current
  setMessages((prev) => prev.map((m) => (m.id === id ? { ... } : m)))
}
```

Cualquier hook nuevo que acumule estado a través de iteraciones de un
`for await`/generador (como el streaming de `/api/chat`) debe seguir este
mismo patrón — id/acumulador en un `ref`, updater de `setState` puro.

## Streaming SSE — por qué `fetch`+`ReadableStream`, no `EventSource`

`EventSource` nativo del browser solo soporta `GET`, y `/api/chat` necesita
`POST` con body (`model`, `history[]`, etc.). `api/client.ts::streamChat`
usa `fetch` con `response.body.getReader()` y parsea manualmente los
bloques `data: ...\n\n` — si se toca ese parser, mantener el buffering
(`buffer += decoder.decode(value, {stream: true})`) porque los chunks TCP
no respetan los límites de evento SSE.

## Componentes vs hooks — dónde va cada cosa

- **Hooks** (`hooks/`) contienen todo el estado y la lógica de
  orquestación (llamadas a `api/client.ts`, manejo de streaming). Nunca
  importan JSX.
- **Componentes** (`components/`) son mayormente de presentación: reciben
  props, renderizan, disparan callbacks. `ChatPanel.tsx` es la excepción
  intencional (mantiene el `input` local del textarea) — estado de UI
  puramente local y efímero puede vivir en el componente, estado que
  sobrevive turnos de conversación va en el hook.

## Testing (ver `.claude/rules/testing.md` para el detalle completo)

- Playwright (`ui/e2e/`) contra el backend Django **real**, nunca mocks —
  es la capa que atrapa bugs de integración invisibles en aislamiento
  (ver el bug del closure arriba). `pnpm --filter ui exec playwright test`.
- No hay tests unitarios de componentes React en este proyecto todavía
  (Vitest/Testing Library) — Playwright end-to-end cubre el caso de uso
  real hasta que la superficie de componentes crezca lo suficiente para
  justificar la capa extra (KISS: no agregar el framework de test antes
  de que la necesidad sea concreta).
