import { Clock, MapPin, Navigation, Sparkles } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

type HomeStatsProps = {
  loading: boolean
  placesCount: number
}

type StatItem = {
  label: string
  value: string
  Icon: LucideIcon
}

const buildStats = (loading: boolean, placesCount: number): StatItem[] => [
  { label: 'Места в базе', value: loading ? '...' : String(placesCount), Icon: MapPin },
  { label: 'Рядом со мной', value: 'геопоиск', Icon: Navigation },
  { label: 'Открыто сейчас', value: 'по часам', Icon: Clock },
  { label: 'Маршруты', value: 'AI-подбор', Icon: Sparkles },
]

export const HomeStats = ({ loading, placesCount }: HomeStatsProps) => {
  const stats = buildStats(loading, placesCount)

  return (
    <section className="stats-grid">
      {stats.map(({ label, value, Icon }) => (
        <article className="stat-card" key={label}>
          <span className="stat-icon">
            <Icon size={19} />
          </span>
          <span className="stat-label">{label}</span>
          <strong className="stat-value">{value}</strong>
        </article>
      ))}
    </section>
  )
}
