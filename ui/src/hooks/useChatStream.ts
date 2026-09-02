import { useCallback, useRef, useState } from "react"
import { confirmShell, streamChat } from "../api/client"
import type { Agent, ChatMessage, Device } from "../api/types"

export interface ChatSettings {
  model: string
  device: Device
  agent: Agent
  maxTokens: number
  noThink: boolean
  allowShell: boolean
  allowSearch: boolean
  systemFileContent: string
}

interface PendingRun {
  command: string
}

interface DisplayMessage extends ChatMessage {
  id: string
}

let nextId = 0
function makeId(): string {
  nextId += 1
  return `msg-${nextId}`
}

function formatConversation(messages: DisplayMessage[]): string {
  return messages.map((m) => `[${m.role}]\n${m.content}`).join("\n\n")
}

export function useChatStream(settings: ChatSettings) {
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [pendingRun, setPendingRun] = useState<PendingRun | null>(null)
  const [tokensPerSecond, setTokensPerSecond] = useState<number | null>(null)
  const historyRef = useRef<ChatMessage[]>([])

  const assistantIdRef = useRef<string | null>(null)

  const consumeStream = useCallback(async (history: ChatMessage[]) => {
    setIsStreaming(true)
    const start = performance.now()
    let tokenCount = 0
    assistantIdRef.current = null

    try {
      for await (const event of streamChat({
        model: settings.model,
        device: settings.device,
        agent: settings.agent,
        max_tokens: settings.maxTokens,
        no_think: settings.noThink,
        allow_shell: settings.allowShell,
        allow_search: settings.allowSearch,
        system_file_content: settings.systemFileContent,
        history,
      })) {
        if (event.kind === "token") {
          tokenCount += 1
          const text = String(event.payload.text ?? "")
          if (assistantIdRef.current === null) {
            const id = makeId()
            assistantIdRef.current = id
            setMessages((prev) => [...prev, { id, role: "assistant", content: text }])
          } else {
            const id = assistantIdRef.current
            setMessages((prev) =>
              prev.map((m) => (m.id === id ? { ...m, content: m.content + text } : m)),
            )
          }
        } else if (event.kind === "tool_result") {
          const text = String(event.payload.text ?? "")
          const tool = String(event.payload.tool ?? "tool")
          setMessages((prev) => [
            ...prev,
            { id: makeId(), role: "system", content: `[tool usada: ${tool}]\n${text}` },
          ])
          assistantIdRef.current = null
        } else if (event.kind === "memory_recalled") {
          const text = String(event.payload.text ?? "")
          setMessages((prev) => [
            ...prev,
            { id: makeId(), role: "system", content: `[tool usada: memory]\n${text}` },
          ])
        } else if (event.kind === "run_proposed") {
          setPendingRun({ command: String(event.payload.command ?? "") })
        }
      }
      const elapsed = (performance.now() - start) / 1000
      setTokensPerSecond(elapsed > 0 ? tokenCount / elapsed : null)
    } finally {
      setIsStreaming(false)
    }
  }, [settings])

  const send = useCallback(
    async (userText: string) => {
      const userMessage: ChatMessage = { role: "user", content: userText }
      historyRef.current = [...historyRef.current, userMessage]
      setMessages((prev) => [
        ...prev,
        { id: makeId(), role: "user", content: userText },
      ])
      await consumeStream(historyRef.current)
    },
    [consumeStream],
  )

  const approveRun = useCallback(async () => {
    if (pendingRun === null) return
    const command = pendingRun.command
    setPendingRun(null)
    const outcome = await confirmShell(command)
    const resultText = outcome.blocked_reason
      ? `[comando bloqueado: ${command} — motivo: ${outcome.blocked_reason}]`
      : `[resultado de ejecutar '${command}': code=${outcome.return_code}, stdout=${JSON.stringify(outcome.stdout)}, stderr=${JSON.stringify(outcome.stderr)}]`
    historyRef.current = [
      ...historyRef.current,
      { role: "system", content: resultText },
    ]
    setMessages((prev) => [
      ...prev,
      { id: makeId(), role: "system", content: resultText },
    ])
    await consumeStream(historyRef.current)
  }, [pendingRun, consumeStream])

  const rejectRun = useCallback(() => {
    if (pendingRun === null) return
    const command = pendingRun.command
    setPendingRun(null)
    const resultText = `[comando no ejecutado: ${command} — el usuario no confirmó]`
    historyRef.current = [
      ...historyRef.current,
      { role: "system", content: resultText },
    ]
    setMessages((prev) => [
      ...prev,
      { id: makeId(), role: "system", content: resultText },
    ])
  }, [pendingRun])

  const newConversation = useCallback(() => {
    historyRef.current = []
    setMessages([])
    setPendingRun(null)
    setTokensPerSecond(null)
  }, [])

  const copyConversation = useCallback(async () => {
    await navigator.clipboard.writeText(formatConversation(messages))
  }, [messages])

  const exportConversation = useCallback(async () => {
    const text = formatConversation(messages)
    const filename = `local-llm-lab-chat-${new Date().toISOString().replace(/[:.]/g, "-")}.txt`

    const w = window as unknown as { __TAURI_INTERNALS__?: unknown }
    if (w.__TAURI_INTERNALS__ === undefined) {
      const blob = new Blob([text], { type: "text/plain" })
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      return
    }

    const { save } = await import("@tauri-apps/plugin-dialog")
    const { writeTextFile } = await import("@tauri-apps/plugin-fs")
    const path = await save({ defaultPath: filename })
    if (path === null) return
    await writeTextFile(path, text)
  }, [messages])

  return {
    messages,
    send,
    isStreaming,
    pendingRun,
    approveRun,
    rejectRun,
    tokensPerSecond,
    newConversation,
    exportConversation,
    copyConversation,
  }
}
