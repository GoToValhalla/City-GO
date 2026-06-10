import { useCallback, useEffect, useState } from 'react'
import {
  approvePlaceImage,
  fetchPendingPlaceImages,
  rejectPlaceImage,
  setPrimaryPlaceImage,
  type PendingPlaceImage,
} from '../../api/admin/placeImageReview.api'
import '../../styles/admin.css'

const DEFAULT_CITY = 'zelenogradsk'

export const PhotoReviewPage = () => {
  const [items, setItems] = useState<PendingPlaceImage[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [brokenImages, setBrokenImages] = useState<Record<number, boolean>>({})

  const loadQueue = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchPendingPlaceImages(DEFAULT_CITY, 50, 0)
      setItems(data.items)
      setTotal(data.total)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load queue')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadQueue()
  }, [loadQueue])

  const runAction = async (
    imageId: number,
    action: 'approve' | 'reject' | 'set-primary',
  ) => {
    setBusyId(imageId)
    setError(null)
    try {
      if (action === 'approve') await approvePlaceImage(imageId)
      if (action === 'reject') await rejectPlaceImage(imageId)
      if (action === 'set-primary') await setPrimaryPlaceImage(imageId)
      setItems((current) => current.filter((item) => item.image_id !== imageId))
      setTotal((current) => Math.max(0, current - 1))
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Action failed')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <main className="admin-photo-review">
      <header className="admin-photo-review-header">
        <h1>Photo Review Queue</h1>
        <p>
          Pending images for manual validation. Only approved photos are shown in public catalog.
        </p>
        <div className="admin-photo-review-meta">
          <span>City: {DEFAULT_CITY}</span>
          <span>Pending: {total}</span>
          <button type="button" onClick={() => void loadQueue()} disabled={loading}>
            Refresh
          </button>
        </div>
      </header>

      {loading ? <p className="admin-photo-review-status">Loading queue…</p> : null}
      {error ? <p className="admin-photo-review-error">{error}</p> : null}

      {!loading && items.length === 0 ? (
        <p className="admin-photo-review-status">No pending images.</p>
      ) : null}

      <section className="admin-photo-review-grid">
        {items.map((item) => {
          const imageBroken = brokenImages[item.image_id] === true
          const mapUrl = `https://www.openstreetmap.org/?mlat=${item.place_lat}&mlon=${item.place_lng}#map=17/${item.place_lat}/${item.place_lng}`

          return (
            <article key={item.image_id} className="admin-photo-card">
              <div className="admin-photo-card-media">
                {imageBroken ? (
                  <div className="admin-photo-card-fallback">image unavailable</div>
                ) : (
                  <img
                    src={item.thumbnail_url ?? item.image_url}
                    alt={item.place_title}
                    onError={() => {
                      setBrokenImages((current) => ({ ...current, [item.image_id]: true }))
                    }}
                  />
                )}
              </div>

              <div className="admin-photo-card-body">
                <h2>{item.place_title}</h2>
                <p>{item.place_address ?? 'Address unavailable'}</p>
                <ul>
                  <li>Category: {item.place_category ?? '—'}</li>
                  <li>City: {item.city_slug ?? '—'}</li>
                  <li>Coords: {item.place_lat}, {item.place_lng}</li>
                  <li>Source: {item.source_type}</li>
                  <li>Confidence: {item.confidence ?? '—'}</li>
                  <li>Attribution: {item.attribution ?? '—'}</li>
                  <li>License: {item.license ?? '—'}</li>
                </ul>

                <div className="admin-photo-card-actions">
                  <button
                    type="button"
                    disabled={busyId === item.image_id}
                    onClick={() => void runAction(item.image_id, 'approve')}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="danger"
                    disabled={busyId === item.image_id}
                    onClick={() => void runAction(item.image_id, 'reject')}
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    disabled={busyId === item.image_id}
                    onClick={() => void runAction(item.image_id, 'set-primary')}
                  >
                    Set primary
                  </button>
                  {item.source_url ? (
                    <a href={item.source_url} target="_blank" rel="noreferrer">
                      Open source
                    </a>
                  ) : null}
                  <a href={mapUrl} target="_blank" rel="noreferrer">
                    Open map
                  </a>
                </div>
              </div>
            </article>
          )
        })}
      </section>
    </main>
  )
}
