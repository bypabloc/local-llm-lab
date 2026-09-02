import { isTauri } from "../lib/tauri"

async function reloadWebview() {
  window.location.reload()
}

async function restartApp() {
  if (!isTauri()) {
    window.location.reload()
    return
  }
  const { relaunch } = await import("@tauri-apps/plugin-process")
  await relaunch()
}

const buttonClass =
  "rounded px-2 py-1 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"

export function AppToolbar() {
  return (
    <div className="flex shrink-0 gap-2 border-b border-slate-200 px-3 py-1.5 dark:border-slate-700">
      <button type="button" className={buttonClass} onClick={() => void reloadWebview()}>
        Recargar ventana
      </button>
      <button type="button" className={buttonClass} onClick={() => void restartApp()}>
        Reiniciar app
      </button>
    </div>
  )
}
