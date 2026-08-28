import { useEffect, useState } from "react"
import { downloadModel, fetchModels, fetchSettings, saveSettings } from "../api/client"
import type { AppSettings, ModelInfo } from "../api/types"
import { isTauri } from "../lib/tauri"

interface Props {
  onClose: () => void
  initialTab?: Tab
}

type Tab = "general" | "models"

async function pickDirectory(): Promise<string | null> {
  if (!isTauri()) return null
  const { open } = await import("@tauri-apps/plugin-dialog")
  const dir = await open({ directory: true })
  return typeof dir === "string" ? dir : null
}

const labelClass = "flex flex-col gap-1 text-sm text-slate-700 dark:text-slate-300"
const inputClass =
  "rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
const buttonClass =
  "rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-40 dark:bg-slate-200 dark:text-slate-900 dark:hover:bg-slate-300"

export function SettingsView({ onClose, initialTab = "general" }: Props) {
  const [tab, setTab] = useState<Tab>(initialTab)

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <header className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Settings</h2>
        <button type="button" className={buttonClass} onClick={onClose}>
          Cerrar
        </button>
      </header>

      <div className="my-3 flex gap-1 border-b border-slate-200 dark:border-slate-700">
        {(["general", "models"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 text-sm capitalize ${
              tab === t
                ? "border-b-2 border-slate-800 font-medium dark:border-slate-200"
                : "text-slate-500 dark:text-slate-400"
            }`}
          >
            {t === "general" ? "General" : "Models"}
          </button>
        ))}
      </div>

      {tab === "general" ? <GeneralTab /> : <ModelsTab />}
    </div>
  )
}

function GeneralTab() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    fetchSettings()
      .then(setSettings)
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : String(err)))
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

  if (loadError) {
    return <p className="text-sm text-red-600">No se pudieron cargar los settings: {loadError}</p>
  }

  if (!settings) {
    return <p className="text-sm text-slate-500">Cargando settings...</p>
  }

  return (
    <>
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
            onChange={(e) => setSettings({ ...settings, models_dir: e.target.value || null })}
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

      <button
        type="button"
        className={buttonClass}
        onClick={() => void handleSave()}
        disabled={saving}
      >
        {saving ? "Guardando..." : "Guardar"}
      </button>
    </>
  )
}

interface DownloadState {
  downloaded: number
  total: number
  status: "downloading" | "done" | "error"
  errorText?: string
}

function ModelsTab() {
  const [models, setModels] = useState<ModelInfo[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [downloads, setDownloads] = useState<Record<string, DownloadState>>({})

  function reloadModels() {
    fetchModels()
      .then(setModels)
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : String(err)))
  }

  useEffect(reloadModels, [])

  async function handleDownload(name: string) {
    setDownloads((prev) => ({ ...prev, [name]: { downloaded: 0, total: 0, status: "downloading" } }))
    try {
      for await (const event of downloadModel(name)) {
        if (event.kind === "progress") {
          setDownloads((prev) => ({
            ...prev,
            [name]: {
              downloaded: event.payload.downloaded ?? 0,
              total: event.payload.total ?? 0,
              status: "downloading",
            },
          }))
        } else if (event.kind === "done") {
          setDownloads((prev) => ({ ...prev, [name]: { ...prev[name], status: "done" } }))
          reloadModels()
        } else if (event.kind === "error") {
          setDownloads((prev) => ({
            ...prev,
            [name]: { ...prev[name], status: "error", errorText: event.payload.text },
          }))
        }
      }
    } catch (err: unknown) {
      setDownloads((prev) => ({
        ...prev,
        [name]: {
          downloaded: 0,
          total: 0,
          status: "error",
          errorText: err instanceof Error ? err.message : String(err),
        },
      }))
    }
  }

  if (loadError) {
    return <p className="text-sm text-red-600">No se pudieron cargar los modelos: {loadError}</p>
  }

  if (!models) {
    return <p className="text-sm text-slate-500">Cargando modelos...</p>
  }

  return (
    <ul className="flex flex-col gap-3">
      {models.map((m) => {
        const dl = downloads[m.name]
        const percent = dl && dl.total > 0 ? Math.round((dl.downloaded / dl.total) * 100) : 0
        return (
          <li
            key={m.name}
            className="flex flex-col gap-1 rounded border border-slate-200 p-3 dark:border-slate-700"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{m.name}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {m.n_ctx} ctx · {m.license}
              </span>
            </div>

            {m.is_downloaded ? (
              <span className="text-xs text-green-600 dark:text-green-400">Descargado</span>
            ) : dl?.status === "downloading" ? (
              <div className="flex flex-col gap-1">
                <div className="h-2 w-full overflow-hidden rounded bg-slate-200 dark:bg-slate-700">
                  <div
                    className="h-full bg-slate-800 dark:bg-slate-200"
                    style={{ width: `${percent}%` }}
                  />
                </div>
                <span className="text-xs text-slate-500 dark:text-slate-400">{percent}%</span>
              </div>
            ) : dl?.status === "error" ? (
              <span className="text-xs text-red-600">{dl.errorText ?? "descarga falló"}</span>
            ) : m.downloadable ? (
              <button
                type="button"
                className={`${buttonClass} self-start`}
                onClick={() => void handleDownload(m.name)}
              >
                Descargar
              </button>
            ) : (
              <span className="text-xs text-slate-500 dark:text-slate-400">
                No disponible para descarga automática — copiar el .gguf manualmente
              </span>
            )}
          </li>
        )
      })}
    </ul>
  )
}
