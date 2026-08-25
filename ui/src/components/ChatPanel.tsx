import { useState } from "react"
import type { useChatStream } from "../hooks/useChatStream"
import { MessageBubble } from "./MessageBubble"
import { RunConfirmCard } from "./RunConfirmCard"

interface Props {
  chat: ReturnType<typeof useChatStream>
}

export function ChatPanel({ chat }: Props) {
  const { messages, send, isStreaming, pendingRun, approveRun, rejectRun, tokensPerSecond } = chat
  const [input, setInput] = useState("")

  async function handleSend() {
    const text = input.trim()
    if (!text || isStreaming) return
    setInput("")
    await send(text)
  }

  return (
    <div className="chat-panel">
      <header className="chat-panel__header">
        <span>local-llm-lab chat</span>
        {tokensPerSecond !== null && (
          <span className="chat-panel__tps">{tokensPerSecond.toFixed(1)} tok/s</span>
        )}
      </header>

      <div className="chat-panel__messages">
        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role} content={m.content} />
        ))}
        {pendingRun && (
          <RunConfirmCard
            command={pendingRun.command}
            onApprove={approveRun}
            onReject={rejectRun}
          />
        )}
      </div>

      <div className="chat-panel__input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              void handleSend()
            }
          }}
          placeholder="Escribí un mensaje..."
          disabled={isStreaming || pendingRun !== null}
        />
        <button
          type="button"
          onClick={() => void handleSend()}
          disabled={isStreaming || pendingRun !== null}
        >
          Enviar
        </button>
      </div>
    </div>
  )
}
