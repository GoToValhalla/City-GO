import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { adminGet, adminPost } from './adminApi'
import { AdminCityWorkspacePanels } from './AdminCityWorkspacePanels'
import type { AdminCityPublicationResponse, AdminCityWorkspaceResponse } from './adminTypes'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

type AdminActionResponse = {
  message?: string
}

export const AdminCityWorkspacePage = () => {
  const { slug = '' } = useParams()
  const [data, setData] = useState<AdminCityWorkspaceResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(() => {
    setLoading(true)
    setError(null)
    adminGet<AdminCityWorkspaceResponse>(`/admin/cities/by-slug/${slug}/workspace`)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [slug])

  useEffect(() => { reload() }, [reload])

  const runImportAction = async (action: string) => {
    if (!data) return
    if (action === 'cancel' && !window.confirm(`Отменить импорт города ${data.city.name}?`)) return
    setBusy(action)
    setNotice(null)
    setError(null)
    try {
      const response = await adminPost<AdminActionResponse>(`/admin/import-jobs/${data.city.id}/${action}`, {})
      setNotice(response.message ?? 'Действие выполнено.')
      reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка действия')
    } finally {
      setBusy(null)
    }
  }

  const publish = async () => {
    if (!data || !window.confirm(`Опубликовать город ${data.city.name}?`)) return
    setBusy('publish')
    try {
      const response = await adminPost<AdminCityPublicationResponse>(`/admin/cities/${data.city.id}/publish`, {})
      setNotice(response.message)
      reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка публикации')
    } finally { setBusy(null) }
  }

  const unpublish = async () => {
    if (!data) return
    const reason = window.prompt(`Причина снятия ${data.city.name} с публикации`, 'Ручное снятие с публикации')
    if (!reason) return
    setBusy('unpublish')
    try {
      const response = await adminPost<AdminCityPublicationResponse>(`/admin/cities/${data.city.id}/unpublish`, { reason })
      setNotice(response.message)
      reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка снятия с публикации')
    } finally { setBusy(null) }
  }

  if (loading) return <AdminLoading />
  if (error) return <AdminError message={error} />
  if (!data) return <AdminEmpty message="Город не найден" />

  return (
    <div>
      <Link to="/admin/cities" className="admin-muted">← Все города</Link>
      <h2 className="admin-page-title">{data.city.name}</h2>
      <p className="admin-page-subtitle">{data.city.slug} · {data.city.country} · {data.city.region ?? 'регион не указан'}</p>
      {notice && <p className="admin-success-text">{notice}</p>}
      {data.import_job.is_stalled && <p className="admin-error-text">Import job возможно завис: нет heartbeat дольше порога.</p>}
      <AdminCityWorkspacePanels
        data={data}
        busy={busy}
        onImportAction={(action) => { void runImportAction(action) }}
        onPublish={() => { void publish() }}
        onUnpublish={() => { void unpublish() }}
      />
    </div>
  )
}
