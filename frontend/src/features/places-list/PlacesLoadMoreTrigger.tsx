import { useEffect, useRef } from 'react'

type Props = {
  onVisible: () => void
  loading: boolean
  hasMore: boolean
}

/**
 * Невидимый sentinel-элемент внизу списка.
 * Вызывает onVisible() когда появляется в видимой области экрана
 * (IntersectionObserver, rootMargin 300px — предзагрузка).
 */
export const PlacesLoadMoreTrigger = ({ onVisible, loading, hasMore }: Props) => {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el || !hasMore || loading) return

    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) onVisible() },
      { rootMargin: '300px' },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [onVisible, loading, hasMore])

  if (!hasMore) return null

  return <div ref={ref} className="places-load-more" aria-hidden="true" />
}
