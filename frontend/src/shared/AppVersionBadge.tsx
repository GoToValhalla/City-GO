import { useEffect, useMemo, useState } from 'react'
import { buildApiUrl } from './api/http'
import { fetchBackendVersion, type BackendVersion } from './api/appVersion'
import { env } from './config/env'
import { frontendBuildInfo } from './config/buildInfo'

const STORAGE_KEY = 'city-go-debug-panel-hidden'

type HealthPayload = {
  status?: string
  [key: string]: unknown
}

type ServiceProbe<T> = {
  status: 'loading' | 'ok' | 'error'
  data: T | null
  error: string | null
  checkedAt: string | null
}

const initialProbe = <T,>(): ServiceProbe<T> => ({
  status: 'loading',
  data: null,
  error: null,
  checkedAt: null,
})

const readHiddenState = (): boolean => {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

const persistHiddenState = (hidden: boolean): void => {
  try {
    window.localStorage.setItem(STORAGE_KEY, hidden ? '1' : '0')
  } catch {
    // localStorage can be blocked in private mode; the panel still works for the session.
  }
}

const buildHealthUrl = (): string => buildApiUrl('/health')

const fetchHealth = async (): Promise<HealthPayload> => {
  const response = await fetch(buildHealthUrl())
  if (!response.ok) {
    throw new Error(`Health request failed: HTTP ${response.status}`)
  }
  return response.json()
}

export function AppVersionBadge() {
  const [hidden, setHidden] = useState(readHiddenState)
  const [backendVersion, setBackendVersion] = useState<ServiceProbe<BackendVersion>>(initialProbe)
  const [backendHealth, setBackendHealth] = useState<ServiceProbe<HealthPayload>>(initialProbe)
  const [now, setNow] = useState(() => new Date().toISOString())

  const runtimeInfo = useMemo(() => ({
    page: window.location.href,
    userAgent: window.navigator.userAgent,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  }), [])

  const refresh = () => {
    const checkedAt = new Date().toISOString()

    setBackendVersion({ ...initialProbe<BackendVersion>(), checkedAt })
    fetchBackendVersion()
      .then((data) => setBackendVersion({ status: 'ok', data, error: null, checkedAt }))
      .catch((error: unknown) => setBackendVersion({
        status: 'error',
        data: null,
        error: error instanceof Error ? error.message : String(error),
        checkedAt,
      }))

    setBackendHealth({ ...initialProbe<HealthPayload>(), checkedAt })
    fetchHealth()
      .then((data) => setBackendHealth({ status: 'ok', data, error: null, checkedAt }))
      .catch((error: unknown) => setBackendHealth({
        status: 'error',
        data: null,
        error: error instanceof Error ? error.message : String(error),
        checkedAt,
      }))
  }

  useEffect(() => {
    refresh()
    const clock = window.setInterval(() => setNow(new Date().toISOString()), 30_000)
    return () => window.clearInterval(clock)
  }, [])

  const hide = () => {
    persistHiddenState(true)
    setHidden(true)
  }

  const show = () => {
    persistHiddenState(false)
    setHidden(false)
    refresh()
  }

  if (hidden) {
    return (
      <button className="app-debug-toggle" type="button" onClick={show}>
        Debug
      </button>
    )
  }

  const backendSha = backendVersion.data?.build_sha_short ?? backendVersion.status
  const backendRun = backendVersion.data?.build_run_number ?? backendVersion.status
  const healthStatus = backendHealth.data?.status ?? backendHealth.status

  return (
    <aside className="app-debug-panel" aria-label="City Go debug panel">
      <div className="app-debug-header">
        <strong>City Go Debug</strong>
        <div className="app-debug-actions">
          <button type="button" onClick={refresh}>Обновить</button>
          <button type="button" onClick={hide}>Скрыть</button>
        </div>
      </div>

      <div className="app-debug-grid">
        <span>FE sha</span><strong>{frontendBuildInfo.buildShaShort}</strong>
        <span>FE run</span><strong>{frontendBuildInfo.buildRunNumber}</strong>
        <span>FE time</span><strong>{frontendBuildInfo.buildTime}</strong>
        <span>BE sha</span><strong>{backendSha}</strong>
        <span>BE run</span><strong>{backendRun}</strong>
        <span>BE time</span><strong>{backendVersion.data?.build_time ?? backendVersion.status}</strong>
        <span>BE health</span><strong>{healthStatus}</strong>
        <span>API base</span><strong>{env.apiBaseUrl}</strong>
        <span>useBackend</span><strong>{String(env.useBackend)}</strong>
        <span>now</span><strong>{now}</strong>
      </div>

      <details className="app-debug-details">
        <summary>Служебная информация</summary>
        <pre>{JSON.stringify({
          frontend: frontendBuildInfo,
          backendVersion,
          backendHealth,
          endpoints: {
            version: buildApiUrl('/version'),
            health: buildHealthUrl(),
          },
          runtime: runtimeInfo,
        }, null, 2)}</pre>
      </details>
    </aside>
  )
}
