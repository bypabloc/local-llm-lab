export type Role = "system" | "user" | "assistant"

export interface ChatMessage {
  role: Role
  content: string
}

export type Device = "cpu" | "gpu" | null
export type Agent = "jarvis" | "tars" | "gemma"

export interface ModelInfo {
  name: string
  n_ctx: number
  license: string
}

export interface ChatRequest {
  model: string
  device: Device
  agent: Agent
  max_tokens: number
  no_think: boolean
  allow_shell: boolean
  allow_search: boolean
  system_file_content: string
  history: ChatMessage[]
}

export type ChatEventKind =
  | "token"
  | "run_proposed"
  | "tool_result"
  | "assistant_done"

export interface ChatEvent {
  kind: ChatEventKind
  payload: Record<string, unknown>
}

export interface CommandOutcome {
  command: string
  executed: boolean
  blocked_reason: string | null
  stdout: string
  stderr: string
  return_code: number | null
}

export interface BenchRequest {
  models: string[]
  prompt: string
  max_tokens: number
  no_think: boolean
  device: Device
  system_file_content?: string
}

export interface BenchResult {
  model: string
  device: string
  tokens_per_second: number
  total_seconds: number
  prefill_seconds: number
  generation_seconds: number
  prompt_tokens: number
  completion_tokens: number
  rating: "fluido" | "aceptable" | "lento"
  no_think: boolean
  text: string
}
