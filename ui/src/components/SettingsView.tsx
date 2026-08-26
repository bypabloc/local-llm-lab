import { useEffect, useState } from "react"
import { fetchSettings, saveSettings } from "../api/client"
import type { AppSettings } from "../api/types"
import { isTauri } from "../lib/tauri"

interface Props {
  onClose: () => void
}

async function pickDirectory(): Promise<string | null> {
  if (!isTauri()) return null
  const { open } = await import("@tauri-apps/plugin-dialog")
  const dir = await open({ directory: true })
  return typeof dir === "string" ? dir : null
}

export function SettingsView({ onClose }: Props) {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchSettings().then(setSettings)
  }, [])

  async function handleSave() {
    if (!settings) return
    setSaving(true)
    try {
      setSettings(await saveSettings(settings))
    } finally {
      setSaving(false)
    }
  }

  const labelClass = "flex flex-col gap-1 text-sm text-slate-700 dark:text-slate-300"
  const inputClass =
    "rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
  const buttonClass =
    "rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-40 dark:bg-slate-200 dark:text-slate-900 dark:hover:bg-slate-300"

  if (!settings) {
    return (
      <div className="flex-1 overflow-y-auto p-4">
        <p className="text-sm text-slate-500">Cargando settings...</p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Settings</h2>
        <button type="button" className={buttonClass} onClick={onClose}>
          Cerrar
        </button>
      </header>

      <label className={`${labelClass} my-3`}>
        Ruta de memory.db
        <div className="flex gap-2">
          <input
            className={`${inputClass} flex-1`}
            value={settings.memory_db_path}
            onChange={(e) => setSettings({ ...settings, memory_db_path: e.target.value })}
          />
          {isTauri() && (
            <button
              type="button"
              className={buttonClass}
              onClick={() =>
                void pickDirectory().then((dir) => {
                  if (dir) setSettings({ ...settings, memory_db_path: `${dir}/memory.db` })
                })
              }
            >
              Elegir carpeta
            </button>
          )}
        </div>
      </label>

      <label className={`${labelClass} mb-3`}>
        Directorio de modelos GGUF
        <div className="flex gap-2">
          <input
            className={`${inputClass} flex-1`}
            value={settings.models_dir ?? ""}
            placeholder="(default: models/ en la raíz del proyecto)"
            onChange={(e) =>
              setSettings({ ...settings, models_dir: e.target.value || null })
            }
          />
          {isTauri() && (
            <button
              type="button"
              className={buttonClass}
              onClick={() =>
                void pickDirectory().then((dir) => {
                  if (dir) setSettings({ ...settings, models_dir: dir })
                })
              }
            >
              Elegir carpeta
            </button>
          )}
        </div>
      </label>

      <button type="button" className={buttonClass} onClick={() => void handleSave()} disabled={saving}>
        {saving ? "Guardando..." : "Guardar"}
      </button>
    </div>
  )
}
