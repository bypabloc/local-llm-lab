import { isTauri } from "../lib/tauri"
import type {
  AppSettings,
  BenchRequest,
  BenchResult,
  ChatEvent,
  ChatRequest,
  CommandOutcome,
  DownloadEvent,
  ModelInfo,
} from "./types"

// ponytail: puerto fijo (8000) cuando corre fuera de Tauri (pnpm dev
// standalone); dentro de Tauri, el sidecar bindea a un puerto efímero
// elegido por Rust y este invoke lo descubre en runtime.
async function resolveBaseUrl(): Promise<string> {
  if (!isTauri()) {
    return "http://127.0.0.1:8000/api"
  }
  const { invoke } = await import("@tauri-apps/api/core")
  const port = await invoke<number>("get_server_port")
  return `http://127.0.0.1:${port}/api`
}

let cachedBaseUrl: Promise<string> | null = null
function getBaseUrl(): Promise<string> {
  cachedBaseUrl ??= resolveBaseUrl()
  return cachedBaseUrl
}

async function* readSseEvents<T>(response: Response): AsyncGenerator<T> {
  if (!response.ok || response.body === null) {
    throw new Error(`stream falló: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let separatorIndex: number
    while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, separatorIndex).trim()
      buffer = buffer.slice(separatorIndex + 2)
      if (!chunk.startsWith("data: ")) continue
      yield JSON.parse(chunk.slice("data: ".length)) as T
    }
  }
}

export async function fetchModels(): Promise<ModelInfo[]> {
  const base = await getBaseUrl()
  const response = await fetch(`${base}/models`)
  if (!response.ok) {
    throw new Error(`GET /models falló: ${response.status}`)
  }
  const body = (await response.json()) as { models: ModelInfo[] }
  return body.models
}

export async function confirmShell(command: string): Promise<CommandOutcome> {
  const base = await getBaseUrl()
  const response = await fetch(`${base}/shell/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command }),
  })
  if (!response.ok) {
    throw new Error(`POST /shell/confirm falló: ${response.status}`)
  }
  return (await response.json()) as CommandOutcome
}

export async function runBench(request: BenchRequest): Promise<BenchResult[]> {
  const base = await getBaseUrl()
  const response = await fetch(`${base}/bench`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    throw new Error(`POST /bench falló: ${response.status}`)
  }
  const body = (await response.json()) as { results: BenchResult[] }
  return body.results
}

export async function fetchSettings(): Promise<AppSettings> {
  const base = await getBaseUrl()
  const response = await fetch(`${base}/settings`)
  if (!response.ok) {
    throw new Error(`GET /settings falló: ${response.status}`)
  }
  return (await response.json()) as AppSettings
}

export async function saveSettings(settings: AppSettings): Promise<AppSettings> {
  const base = await getBaseUrl()
  const response = await fetch(`${base}/settings/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  })
  if (!response.ok) {
    throw new Error(`POST /settings/update falló: ${response.status}`)
  }
  return (await response.json()) as AppSettings
}

export async function* streamChat(
  request: ChatRequest,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const base = await getBaseUrl()
  const response = await fetch(`${base}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  })
  yield* readSseEvents<ChatEvent>(response)
}

export async function* downloadModel(
  model: string,
  signal?: AbortSignal,
): AsyncGenerator<DownloadEvent> {
  const base = await getBaseUrl()
  const response = await fetch(`${base}/models/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model }),
    signal,
  })
  yield* readSseEvents<DownloadEvent>(response)
}
