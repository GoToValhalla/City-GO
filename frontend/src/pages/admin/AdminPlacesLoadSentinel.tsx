import { useEffect, useRef } from 'react'

type Props = {
  enabled: boolean
  loading: boolean
  onLoadMore: () => void
  shown: number
  total: number
}

export const AdminPlacesLoadSentinel = ({ enabled, loading, onLoadMore, shown, total }: Props) => {
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const node = ref.current
    if (!node || !enabled || typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(
      (entries) => { if (entries[0]?.isIntersecting && !loading) onLoadMore() },
      { rootMargin: '240px' },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [enabled, loading, onLoadMore])

  return (
    <div ref={ref} className="admin-load-sentinel">
      <p className="admin-muted">Показано {shown} из {total}</p>
      {enabled && loading && <p className="admin-muted">Загрузка…</p>}
      {enabled && !loading && <p className="admin-muted">Прокрутите вниз для подгрузки</p>}
    </div>
  )
}
