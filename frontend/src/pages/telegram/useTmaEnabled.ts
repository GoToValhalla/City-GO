import { useEffect, useState } from 'react'
import { getPublicFeatures } from '../../api/features/publicFeatures.api'

type TmaEnabledState = {
  loading: boolean
  enabled: boolean
  error: string | null
}

export const useTmaEnabled = (): TmaEnabledState => {
  const [state, setState] = useState<TmaEnabledState>({ loading: true, enabled: false, error: null })

  useEffect(() => {
    let active = true
    getPublicFeatures()
      .then((features) => { if (active) setState({ loading: false, enabled: features.tma_enabled, error: null }) })
      .catch((error) => { if (active) setState({ loading: false, enabled: false, error: error instanceof Error ? error.message : 'Не удалось проверить доступность приложения' }) })
    return () => { active = false }
  }, [])

  return state
}
