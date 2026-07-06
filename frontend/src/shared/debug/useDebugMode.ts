import { useEffect, useState } from 'react'
import { isDebugEnabled, setDebugEnabled } from '../config/debug'

export const useDebugMode = () => {
  const [enabled, setEnabled] = useState(() => isDebugEnabled())

  useEffect(() => {
    const onStorage = () => setEnabled(isDebugEnabled())
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const setDebug = (value: boolean) => {
    setDebugEnabled(value)
    setEnabled(value)
  }

  return { enabled, setDebug }
}
