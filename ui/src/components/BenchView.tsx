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

  return (
    <div className="bench-view">
      <header className="bench-view__header">
        <h2>Bench</h2>
        <button type="button" onClick={onClose}>
          Cerrar
        </button>
      </header>

      <div className="bench-view__models">
        {models.map((m) => (
          <label key={m.name} className="field field--checkbox">
            <input
              type="checkbox"
              checked={selected.includes(m.name)}
              onChange={() => toggle(m.name)}
            />
            {m.name}
          </label>
        ))}
      </div>

      <label className="field">
        Prompt
        <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={2} />
      </label>

      <label className="field">
        Device
        <select
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

      <button type="button" onClick={() => void handleRun()} disabled={running}>
        {running ? "Corriendo..." : "Correr bench"}
      </button>

      {results.length > 0 && (
        <>
          <table className="bench-view__table">
            <thead>
              <tr>
                <th>Modelo</th>
                <th>tok/s</th>
                <th>Total (s)</th>
                <th>Rating</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.model}>
                  <td>{r.model}</td>
                  <td>{r.tokens_per_second.toFixed(2)}</td>
                  <td>{r.total_seconds.toFixed(2)}</td>
                  <td>{r.rating}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button type="button" onClick={exportJson}>
            Exportar JSON
          </button>
        </>
      )}
    </div>
  )
}
