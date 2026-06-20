import { useEffect, useMemo, useState } from 'react'
import { buildApiUrl } from './api/http'
import { fetchBackendVersion, type BackendVersion } from './api/appVersion'
import { env } from './config/env'
import { frontendBuildInfo } from './config/buildInfo'

const STORAGE_KEY = 'city-go-debug-panel-hidden'
const EXPANDED_STORAGE_KEY = 'city-go-debug-panel-expanded'

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

const readLocalFlag = (key: string, defaultValue: boolean): boolean => {
  try {
    const value = window.localStorage.getItem(key)
    if (value === null) return defaultValue
    return value === '1'
  } catch {
    return defaultValue
  }
}

const persistLocalFlag = (key: string, enabled: boolean): void => {
  try {
    window.localStorage.setItem(key, enabled ? '1' : '0')
  } catch {
    return
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
  const [hidden, setHidden] = useState(() => readLocalFlag(STORAGE_KEY, false))
  const [expanded, setExpanded] = useState(() => readLocalFlag(EXPANDED_STORAGE_KEY, false))
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
    persistLocalFlag(STORAGE_KEY, true)
    setHidden(true)
  }

  const show = () => {
    persistLocalFlag(STORAGE_KEY, false)
    setHidden(false)
    refresh()
  }

  const toggleExpanded = () => {
    const nextExpanded = !expanded
    persistLocalFlag(EXPANDED_STORAGE_KEY, nextExpanded)
    setExpanded(nextExpanded)
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
  const panelClassName = expanded ? 'app-debug-panel app-debug-panel--expanded' : 'app-debug-panel'

  return (
    <aside className={panelClassName} aria-label="City Go debug panel">
      <div className="app-debug-header">
        <strong>City Go Debug</strong>
        <div className="app-debug-actions">
          <button type="button" onClick={refresh}>Обновить</button>
          <button type="button" onClick={toggleExpanded}>{expanded ? 'Свернуть' : 'Развернуть'}</button>
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

      {expanded ? (
        <details className="app-debug-details" open>
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
      ) : null}
    </aside>
  )
}
