import { useState } from "react"
import type { useChatStream } from "../hooks/useChatStream"
import { MessageBubble } from "./MessageBubble"
import { RunConfirmCard } from "./RunConfirmCard"

interface Props {
  chat: ReturnType<typeof useChatStream>
}

export function ChatPanel({ chat }: Props) {
  const {
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
  } = chat
  const [input, setInput] = useState("")
  const [copied, setCopied] = useState(false)

  async function handleSend() {
    const text = input.trim()
    if (!text || isStreaming) return
    setInput("")
    await send(text)
  }

  async function handleCopy() {
    await copyConversation()
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-700">
        <span>local-llm-lab chat</span>
        <div className="flex items-center gap-3">
          {tokensPerSecond !== null && (
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {tokensPerSecond.toFixed(1)} tok/s
            </span>
          )}
          <button
            type="button"
            className="rounded px-2 py-1 text-sm text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:hover:bg-transparent dark:text-slate-200 dark:hover:bg-slate-800"
            onClick={() => void handleCopy()}
            disabled={messages.length === 0}
          >
            {copied ? "Copiado" : "Copiar"}
          </button>
          <button
            type="button"
            className="rounded px-2 py-1 text-sm text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:hover:bg-transparent dark:text-slate-200 dark:hover:bg-slate-800"
            onClick={exportConversation}
            disabled={messages.length === 0}
          >
            Exportar
          </button>
          <button
            type="button"
            className="rounded px-2 py-1 text-sm text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:hover:bg-transparent dark:text-slate-200 dark:hover:bg-slate-800"
            onClick={newConversation}
            disabled={isStreaming}
          >
            Nueva conversación
          </button>
        </div>
      </header>

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
        {messages
          .filter((m) => !(m.role === "assistant" && m.content.trimStart().startsWith("REMEMBER:")))
          .map((m) => (
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

      <div className="flex gap-2 border-t border-slate-200 p-4 dark:border-slate-700">
        <textarea
          className="flex-1 resize-none rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
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
          className="rounded bg-slate-800 px-4 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-40 dark:bg-slate-200 dark:text-slate-900 dark:hover:bg-slate-300"
          onClick={() => void handleSend()}
          disabled={isStreaming || pendingRun !== null}
        >
          Enviar
        </button>
      </div>
    </div>
  )
}
