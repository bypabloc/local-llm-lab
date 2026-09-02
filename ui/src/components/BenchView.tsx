import { useState } from "react"
import { runBench } from "../api/client"
import type { BenchResult, Device, ModelInfo } from "../api/types"

interface Props {
  models: ModelInfo[]
  onClose: () => void
}

export function BenchView({ models, onClose }: Props) {
  const [selected, setSelected] = useState<string[]>([])
  const [device, setDevice] = useState<Device>(null)
  const [prompt, setPrompt] = useState("Resumí en 3 puntos qué es Python.")
  const [results, setResults] = useState<BenchResult[]>([])
  const [running, setRunning] = useState(false)

  function toggle(name: string) {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
    )
  }

  async function handleRun() {
    if (selected.length === 0) return
    setRunning(true)
    try {
      const data = await runBench({
        models: selected,
        prompt,
        max_tokens: 1024,
        no_think: false,
        device,
      })
      setResults(data)
    } finally {
      setRunning(false)
    }
  }

  function exportJson() {
    const blob = new Blob([JSON.stringify(results, null, 2)], {
      type: "application/json",
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "bench-results.json"
    a.click()
    URL.revokeObjectURL(url)
  }

  const labelClass = "flex flex-col gap-1 text-sm text-slate-700 dark:text-slate-300"
  const inputClass =
    "rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
  const buttonClass =
    "rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-40 dark:bg-slate-200 dark:text-slate-900 dark:hover:bg-slate-300"

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Bench</h2>
        <button type="button" className={buttonClass} onClick={onClose}>
          Cerrar
        </button>
      </header>

      <div className="my-3 flex flex-wrap gap-3">
        {models.map((m) => (
          <label
            key={m.name}
            className="flex flex-row items-center gap-2 text-sm text-slate-700 dark:text-slate-300"
          >
            <input
              type="checkbox"
              checked={selected.includes(m.name)}
              onChange={() => toggle(m.name)}
            />
            {m.name}
          </label>
        ))}
      </div>

      <label className={`${labelClass} mb-3`}>
        Prompt
        <textarea
          className={`${inputClass} resize-none`}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={2}
        />
      </label>

      <label className={`${labelClass} mb-3`}>
        Device
        <select
          className={inputClass}
          value={device ?? "auto"}
          onChange={(e) =>
            setDevice(e.target.value === "auto" ? null : (e.target.value as Device))
          }
        >
          <option value="auto">auto</option>
          <option value="cpu">cpu</option>
          <option value="gpu">gpu</option>
        </select>
      </label>

      <button type="button" className={buttonClass} onClick={() => void handleRun()} disabled={running}>
        {running ? "Corriendo..." : "Correr bench"}
      </button>

      {results.length > 0 && (
        <>
          <table className="mt-4 w-full border-collapse">
            <thead>
              <tr>
                <th className="border border-slate-300 p-1.5 text-left dark:border-slate-600">
                  Modelo
                </th>
                <th className="border border-slate-300 p-1.5 text-left dark:border-slate-600">
                  tok/s
                </th>
                <th className="border border-slate-300 p-1.5 text-left dark:border-slate-600">
                  Total (s)
                </th>
                <th className="border border-slate-300 p-1.5 text-left dark:border-slate-600">
                  Rating
                </th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.model}>
                  <td className="border border-slate-300 p-1.5 dark:border-slate-600">
                    {r.model}
                  </td>
                  <td className="border border-slate-300 p-1.5 dark:border-slate-600">
                    {r.tokens_per_second.toFixed(2)}
                  </td>
                  <td className="border border-slate-300 p-1.5 dark:border-slate-600">
                    {r.total_seconds.toFixed(2)}
                  </td>
                  <td className="border border-slate-300 p-1.5 dark:border-slate-600">
                    {r.rating}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button type="button" className={`${buttonClass} mt-3`} onClick={exportJson}>
            Exportar JSON
          </button>
        </>
      )}
    </div>
  )
}
