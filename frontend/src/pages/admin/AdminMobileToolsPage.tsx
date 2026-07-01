import { useEffect, useState } from 'react'
import { adminGet } from './adminApi'

type City = { slug: string; name: string; needs_review: number; rejected: number }

export const AdminMobileToolsPage = () => {
  const [cities, setCities] = useState<City[]>([])
  useEffect(() => { void adminGet<{ items: City[] }>('/admin/mobile-tools/cities').then((data) => setCities(data.items)) }, [])
  return <main className="admin-page"><h2 className="admin-page-title">Мобильные инструменты</h2><p>{cities.length}</p></main>
}
