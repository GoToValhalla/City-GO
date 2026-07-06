import { Clock, Coffee, MapPinned, Route } from 'lucide-react'
import { Link } from 'react-router-dom'

const actions = [
  { label: 'Куда сходить', text: 'места для прогулки', to: '/places', Icon: Coffee },
  { label: 'Открыто сейчас', text: 'можно идти без ожидания', to: '/open-now', Icon: Clock },
  { label: 'Места рядом', text: 'по текущей точке', to: '/nearby', Icon: MapPinned },
  { label: 'Собрать прогулку', text: 'маршрут по городу', to: '/routes/generate', Icon: Route },
]

export const QuickActions = () => {
  return (
    <section className="quick-actions" aria-label="Быстрые сценарии">
      {actions.map(({ label, text, to, Icon }) => (
        <Link className="quick-action" key={label} to={to}>
          <Icon size={20} />
          <span>{label}</span>
          <small>{text}</small>
        </Link>
      ))}
    </section>
  )
}
