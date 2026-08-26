import { useState } from "react"
import { AppToolbar } from "./components/AppToolbar"
import { BenchView } from "./components/BenchView"
import { ChatPanel } from "./components/ChatPanel"
import { SettingsView } from "./components/SettingsView"
import { Sidebar } from "./components/Sidebar"
import { useChatStream, type ChatSettings } from "./hooks/useChatStream"
import { useModels } from "./hooks/useModels"

const DEFAULT_SETTINGS: ChatSettings = {
  model: "gemma4-e2b",
  device: null,
  agent: "jarvis",
  maxTokens: 1024,
  noThink: false,
  allowShell: true,
  allowSearch: true,
  systemFileContent: "",
}

export default function App() {
  const { models, error } = useModels()
  const [settings, setSettings] = useState<ChatSettings>(DEFAULT_SETTINGS)
  const [showBench, setShowBench] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const chat = useChatStream(settings)

  return (
    <div className="flex h-screen flex-col bg-white text-slate-900 dark:bg-slate-900 dark:text-slate-100">
      <AppToolbar />
      <div className="relative flex flex-1 min-h-0">
        <Sidebar
          models={models}
          settings={settings}
          onChange={setSettings}
          onOpenBench={() => setShowBench(true)}
          onOpenSettings={() => setShowSettings(true)}
        />
        {error && (
          <div className="absolute inset-x-0 top-0 z-10 bg-red-600 px-3 py-2 text-sm text-white">
            No se pudo conectar al server: {error}
          </div>
        )}
        {showBench ? (
          <BenchView models={models} onClose={() => setShowBench(false)} />
        ) : showSettings ? (
          <SettingsView onClose={() => setShowSettings(false)} />
        ) : (
          <ChatPanel chat={chat} />
        )}
      </div>
    </div>
  )
}
