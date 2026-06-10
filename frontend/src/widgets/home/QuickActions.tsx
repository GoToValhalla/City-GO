import { Clock, Coffee, MapPinned, Route } from 'lucide-react'
import { Link } from 'react-router-dom'

const actions = [
  { label: 'Кофе', text: 'быстрый старт дня', to: '/places', Icon: Coffee },
  { label: 'Открыто', text: 'куда можно сейчас', to: '/open-now', Icon: Clock },
  { label: 'Рядом', text: 'по текущей точке', to: '/nearby', Icon: MapPinned },
  { label: 'Маршрут', text: 'собрать прогулку', to: '/routes/generate', Icon: Route },
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