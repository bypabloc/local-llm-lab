import type { ChangeEvent } from "react"
import type { Agent, Device, ModelInfo } from "../api/types"
import type { ChatSettings } from "../hooks/useChatStream"

interface Props {
  models: ModelInfo[]
  settings: ChatSettings
  onChange: (settings: ChatSettings) => void
  onOpenBench: () => void
}

const AGENTS: Agent[] = ["jarvis", "tars", "gemma"]

export function Sidebar({ models, settings, onChange, onOpenBench }: Props) {
  function patch(partial: Partial<ChatSettings>) {
    onChange({ ...settings, ...partial })
  }

  function handleSystemFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    file.text().then((content) => patch({ systemFileContent: content }))
  }

  return (
    <aside className="sidebar">
      <h1 className="sidebar__title">local-llm-lab</h1>

      <label className="field">
        Modelo
        <select
          value={settings.model}
          onChange={(e) => patch({ model: e.target.value })}
        >
          {models.map((m) => (
            <option key={m.name} value={m.name}>
              {m.name}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        Device
        <select
          value={settings.device ?? "auto"}
          onChange={(e) =>
            patch({ device: e.target.value === "auto" ? null : (e.target.value as Device) })
          }
        >
          <option value="auto">auto</option>
          <option value="cpu">cpu</option>
          <option value="gpu">gpu</option>
        </select>
      </label>

      <label className="field">
        Agent
        <select
          value={settings.agent}
          onChange={(e) => patch({ agent: e.target.value as Agent })}
        >
          {AGENTS.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </label>

      <label className="field field--checkbox">
        <input
          type="checkbox"
          checked={!settings.noThink}
          onChange={(e) => patch({ noThink: !e.target.checked })}
        />
        Thinking
      </label>

      <label className="field field--checkbox">
        <input
          type="checkbox"
          checked={settings.allowShell}
          onChange={(e) => patch({ allowShell: e.target.checked })}
        />
        Shell habilitado
      </label>

      <label className="field field--checkbox">
        <input
          type="checkbox"
          checked={settings.allowSearch}
          onChange={(e) => patch({ allowSearch: e.target.checked })}
        />
        Web search habilitado
      </label>

      <label className="field">
        System prompt
        <input type="file" accept=".md,.txt" onChange={handleSystemFile} />
        <textarea
          value={settings.systemFileContent}
          onChange={(e) => patch({ systemFileContent: e.target.value })}
          rows={4}
        />
      </label>

      <label className="field">
        Max tokens
        <input
          type="number"
          value={settings.maxTokens}
          onChange={(e) => patch({ maxTokens: Number(e.target.value) })}
        />
      </label>

      <button type="button" className="sidebar__bench-button" onClick={onOpenBench}>
        Bench
      </button>
    </aside>
  )
}
