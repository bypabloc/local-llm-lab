import { useCallback, useEffect, useState } from "react"
import { fetchModels } from "../api/client"
import type { ModelInfo } from "../api/types"

export function useModels() {
  const [models, setModels] = useState<ModelInfo[]>([])
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(() => {
    fetchModels()
      .then(setModels)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  useEffect(refresh, [refresh])

  return { models, error, refresh }
}
