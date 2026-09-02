import { useState } from "react"
import { AppToolbar } from "./components/AppToolbar"
import { BenchView } from "./components/BenchView"
import { ChatPanel } from "./components/ChatPanel"
import { SettingsView } from "./components/SettingsView"
import { Sidebar } from "./components/Sidebar"
import { useChatStream, type ChatSettings } from "./hooks/useChatStream"
import { useModels } from "./hooks/useModels"

const DEFAULT_SETTINGS: ChatSettings = {
  model: "agy",
  device: null,
  agent: "jarvis",
  maxTokens: 1024,
  noThink: false,
  allowShell: true,
  allowSearch: true,
  systemFileContent: "",
}

type SettingsTab = "general" | "models"

export default function App() {
  const { models, error, refresh } = useModels()
  const [settings, setSettings] = useState<ChatSettings>(DEFAULT_SETTINGS)
  const [showBench, setShowBench] = useState(false)
  const [settingsTab, setSettingsTab] = useState<SettingsTab | null>(null)
  const chat = useChatStream(settings)

  function closeSettings() {
    setSettingsTab(null)
    refresh()
  }

  return (
    <div className="flex h-screen flex-col bg-white text-slate-900 dark:bg-slate-900 dark:text-slate-100">
      <AppToolbar />
      <div className="relative flex flex-1 min-h-0">
        <Sidebar
          models={models}
          settings={settings}
          onChange={setSettings}
          onOpenBench={() => setShowBench(true)}
          onOpenSettings={() => setSettingsTab("general")}
          onOpenModelDownloads={() => setSettingsTab("models")}
        />
        {error && (
          <div className="absolute inset-x-0 top-0 z-10 bg-red-600 px-3 py-2 text-sm text-white">
            No se pudo conectar al server: {error}
          </div>
        )}
        {showBench ? (
          <BenchView models={models} onClose={() => setShowBench(false)} />
        ) : settingsTab ? (
          <SettingsView onClose={closeSettings} initialTab={settingsTab} />
        ) : (
          <ChatPanel chat={chat} />
        )}
      </div>
    </div>
  )
}
