import type { ChangeEvent } from "react"
import type { Agent, Device, ModelInfo } from "../api/types"
import type { ChatSettings } from "../hooks/useChatStream"

interface Props {
  models: ModelInfo[]
  settings: ChatSettings
  onChange: (settings: ChatSettings) => void
  onOpenBench: () => void
  onOpenSettings: () => void
}

const AGENTS: Agent[] = ["jarvis", "tars", "gemma"]

export function Sidebar({ models, settings, onChange, onOpenBench, onOpenSettings }: Props) {
  function patch(partial: Partial<ChatSettings>) {
    onChange({ ...settings, ...partial })
  }

  function handleSystemFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    file.text().then((content) => patch({ systemFileContent: content }))
  }

  const selectClass =
    "rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
  const labelClass = "flex flex-col gap-1 text-sm text-slate-700 dark:text-slate-300"
  const checkboxLabelClass =
    "flex flex-row items-center gap-2 text-sm text-slate-700 dark:text-slate-300"

  return (
    <aside className="flex w-70 shrink-0 flex-col gap-3 overflow-y-auto border-r border-slate-200 p-4 dark:border-slate-700">
      <h1 className="mb-2 text-lg font-semibold">local-llm-lab</h1>

      <label className={labelClass}>
        Modelo
        <select
          className={selectClass}
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

      <label className={labelClass}>
        Device
        <select
          className={selectClass}
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

      <label className={labelClass}>
        Agent
        <select
          className={selectClass}
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

      <label className={checkboxLabelClass}>
        <input
          type="checkbox"
          checked={!settings.noThink}
          onChange={(e) => patch({ noThink: !e.target.checked })}
        />
        Thinking
      </label>

      <label className={checkboxLabelClass}>
        <input
          type="checkbox"
          checked={settings.allowShell}
          onChange={(e) => patch({ allowShell: e.target.checked })}
        />
        Shell habilitado
      </label>

      <label className={checkboxLabelClass}>
        <input
          type="checkbox"
          checked={settings.allowSearch}
          onChange={(e) => patch({ allowSearch: e.target.checked })}
        />
        Web search habilitado
      </label>

      <label className={labelClass}>
        System prompt
        <input type="file" accept=".md,.txt" onChange={handleSystemFile} className="text-xs" />
        <textarea
          className={`${selectClass} resize-none`}
          value={settings.systemFileContent}
          onChange={(e) => patch({ systemFileContent: e.target.value })}
          rows={4}
        />
      </label>

      <label className={labelClass}>
        Max tokens
        <input
          type="number"
          className={selectClass}
          value={settings.maxTokens}
          onChange={(e) => patch({ maxTokens: Number(e.target.value) })}
        />
      </label>

      <div className="mt-auto flex gap-2">
        <button
          type="button"
          className="flex-1 rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700 dark:bg-slate-200 dark:text-slate-900 dark:hover:bg-slate-300"
          onClick={onOpenBench}
        >
          Bench
        </button>
        <button
          type="button"
          className="flex-1 rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700 dark:bg-slate-200 dark:text-slate-900 dark:hover:bg-slate-300"
          onClick={onOpenSettings}
        >
          Settings
        </button>
      </div>
    </aside>
  )
}
