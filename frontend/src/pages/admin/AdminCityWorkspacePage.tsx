import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminCityWorkspaceTabs } from './AdminCityWorkspaceTabs'
import { WORKSPACE_TABS } from './adminWorkspaceTabs'
import { AdminConfirmDialog } from './AdminConfirmDialog'
import type { AdminCityPublicationResponse, AdminCityWorkspaceResponse } from './adminTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'
import { cityStatusText } from './adminHumanText'

type PendingAction = { kind: string; title: string; message: string; reason?: boolean } | null

export const AdminCityWorkspacePage = () => {
  const { slug = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') ?? 'overview'
  const [data, setData] = useState<AdminCityWorkspaceResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<PendingAction>(null)

  const reload = useCallback(() => {
    setLoading(true)
    adminGet<AdminCityWorkspaceResponse>(`/admin/cities/by-slug/${slug}/workspace`)
      .then(setData).catch((e: Error) => setError(e.message)).finally(() => setLoading(false))
  }, [slug])
  useEffect(() => { reload() }, [reload])

  const execute = async (reason: string) => {
    if (!data || !pending) return
    setBusy(pending.kind); setError(null); setNotice(null)
    try {
      if (pending.kind === 'publish') {
        const row = await adminPost<AdminCityPublicationResponse>(`/admin/cities/${data.city.id}/publish`, {})
        setNotice(row.message)
      } else if (pending.kind === 'unpublish') {
        const row = await adminPost<AdminCityPublicationResponse>(`/admin/cities/${data.city.id}/unpublish`, { reason })
        setNotice(row.message)
      } else {
        const row = await adminPost<{ message?: string }>(`/admin/import-jobs/${data.city.id}/${pending.kind}`, {})
        setNotice(row.message ?? 'Действие выполнено.')
      }
      setPending(null); reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Действие не выполнено')
    } finally { setBusy(null) }
  }

  if (loading) return <AdminLoading />
  if (error && !data) return <AdminError message={error} />
  if (!data) return <AdminEmpty message="Город не найден" />
  const action = (kind: string) => setPending({
    kind, title: kind === 'unpublish' ? 'Снять город с публикации' : 'Подтвердите действие',
    message: `Город: ${data.city.name}`, reason: kind === 'unpublish',
  })

  return (
    <div>
      <Link to="/admin/cities" className="admin-back-link">← Все города</Link>
      <div className="admin-page-header"><div><h2 className="admin-page-title">{data.city.name}</h2><p className="admin-page-subtitle">{data.city.slug} · {cityStatusText(data.city.launch_status)} · готовность {data.readiness.readiness_score}%</p></div></div>
      {notice && <p className="admin-success-text">{notice}</p>}
      {error && <AdminError message={error} />}
      <nav className="admin-tabs" aria-label="Разделы города">{WORKSPACE_TABS.map(([key, label]) => <button type="button" className={`admin-tab${tab === key ? ' active' : ''}`} key={key} onClick={() => setParams({ tab: key })}>{label}</button>)}</nav>
      <AdminCityWorkspaceTabs data={data} tab={tab} busy={busy} onImport={action} onPublish={() => action('publish')} onUnpublish={() => action('unpublish')} />
      <AdminConfirmDialog open={!!pending} title={pending?.title ?? ''} message={pending?.message ?? ''} confirmLabel="Подтвердить" requireReason={pending?.reason} busy={!!busy} onCancel={() => setPending(null)} onConfirm={(reason) => void execute(reason)} />
    </div>
  )
}
