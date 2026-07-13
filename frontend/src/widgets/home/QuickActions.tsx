import { ArrowRight, Clock, List, LocateFixed, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cityCatalogPath, cityRouteBuildPath } from '../../features/city-routing/cityPaths'

type Props = { citySlug: string }

export const QuickActions = ({ citySlug }: Props) => {
  const actions = [
    { label: 'Куда сходить', text: 'Все места города', to: cityCatalogPath(citySlug), Icon: List, primary: true },
    { label: 'Места рядом', text: 'Только по вашему запросу', to: '/nearby', Icon: LocateFixed },
    { label: 'Открыто сейчас', text: 'По опубликованным расписаниям', to: '/open-now', Icon: Clock },
    { label: 'Случайный маршрут', text: 'Готовый сюрприз по городу', to: `${cityRouteBuildPath(citySlug)}?mode=random_mood`, Icon: Sparkles },
  ]

  return <section className="quick-actions" aria-label="Быстрые сценарии">
    {actions.map(({ Icon, label, primary, text, to }) => <Link className={primary ? 'quick-action is-primary' : 'quick-action'} key={label} to={to}>
      <span className="quick-action-icon"><Icon size={23} /></span><span><strong>{label}</strong><small>{text}</small></span><ArrowRight size={20} />
    </Link>)}
  </section>
}
