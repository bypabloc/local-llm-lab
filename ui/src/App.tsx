import { useState } from "react"
import { BenchView } from "./components/BenchView"
import { ChatPanel } from "./components/ChatPanel"
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
  const chat = useChatStream(settings)

  return (
    <div className="app">
      <Sidebar
        models={models}
        settings={settings}
        onChange={setSettings}
        onOpenBench={() => setShowBench(true)}
      />
      {error && <div className="app__error">No se pudo conectar al server: {error}</div>}
      {showBench ? (
        <BenchView models={models} onClose={() => setShowBench(false)} />
      ) : (
        <ChatPanel chat={chat} />
      )}
    </div>
  )
}
