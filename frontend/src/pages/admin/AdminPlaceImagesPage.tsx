import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminPost } from './adminApi'
import { fetchPendingPlaceImages, type PendingPlaceImage } from '../../api/admin/placeImageReview.api'
import { AdminEmpty, AdminError, AdminLoading } from './shared/AdminStates'

export const AdminPlaceImagesPage = () => {
  const [items, setItems] = useState<PendingPlaceImage[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<number | null>(null)
  const [tab, setTab] = useState<'pending' | 'no_photo'>('pending')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchPendingPlaceImages(undefined, 50, 0)
      setItems(data.items)
      setTotal(data.total)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка загрузки')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  const action = async (imageId: number, act: 'approve' | 'reject' | 'set-primary') => {
    if (act === 'reject' && !window.confirm('Отклонить это фото?')) return
    setBusy(imageId)
    try {
      await adminPost(`/admin/place-images/${imageId}/${act}`, act !== 'set-primary' ? {} : undefined)
      setItems((cur) => cur.filter((i) => i.image_id !== imageId))
      setTotal((cur) => Math.max(0, cur - 1))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка действия')
    } finally { setBusy(null) }
  }

  return (
    <div>
      <h2 className="admin-page-title">Фото</h2>
      <div className="admin-tabs">
        <button type="button" className={tab === 'pending' ? 'admin-tab active' : 'admin-tab'} onClick={() => setTab('pending')}>
          На проверке ({total})
        </button>
        <Link className="admin-tab" to="/admin/places?preset=no_photo">Места без фото</Link>
      </div>
      {error && <AdminError message={error} />}
      {loading ? <AdminLoading /> : items.length === 0 ? (
        <AdminEmpty message="Очередь модерации пуста"><p className="admin-muted">Все загруженные фото проверены</p></AdminEmpty>
      ) : (
        <div className="admin-image-grid">
          {items.map((img) => (
            <div key={img.image_id} className="admin-image-card">
              <img src={img.thumbnail_url ?? img.image_url} alt={img.place_title} className="admin-image-thumb" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
              <div className="admin-image-info">
                <div className="admin-image-title">{img.place_title}</div>
                <div className="admin-image-meta">{img.source_type} · {img.confidence != null ? `${Math.round(img.confidence * 100)}%` : '—'}</div>
              </div>
              <div className="admin-image-actions">
                <button disabled={busy === img.image_id} onClick={() => action(img.image_id, 'approve')} className="admin-btn admin-btn-ok" title="Принять">✓</button>
                <button disabled={busy === img.image_id} onClick={() => action(img.image_id, 'set-primary')} className="admin-btn admin-btn-sm" title="Сделать главным">⭐</button>
                <button disabled={busy === img.image_id} onClick={() => action(img.image_id, 'reject')} className="admin-btn admin-btn-danger" title="Отклонить">✕</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
