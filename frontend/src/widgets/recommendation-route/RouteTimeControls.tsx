import { Clock } from 'lucide-react'
import type { RecommendationRouteFormState } from '../../features/routes/model/recommendationRouteForm'

const timePresets = ['60', '120', '180', '240']
const timeOfDayOptions = [
  { value: '', label: 'Гибко' },
  { value: 'now', label: 'Сейчас' },
  { value: 'morning', label: 'Утро' },
  { value: 'afternoon', label: 'День' },
  { value: 'evening', label: 'Вечер' },
]

const routeTimeMode = (value: string) => value === 'now' ? 'now' : 'flexible'

type Props = {
  form: RecommendationRouteFormState
  onChange: (patch: Partial<RecommendationRouteFormState>) => void
}

export const RouteTimeControls = ({ form, onChange }: Props) => (
  <section className="route-control-block" aria-label="Время маршрута">
    <div className="route-control-title">
      <Clock size={18} />
      <span>Сколько времени есть</span>
    </div>
    <div className="route-preset-row">{timePresets.map((minutes) => (
      <button className={form.timeBudgetMinutes === minutes ? 'is-selected' : ''}
        type="button" key={minutes}
        onClick={() => onChange({ useTimeBudget: true, timeBudgetMinutes: minutes })}>
        {Number(minutes) / 60} ч
      </button>
    ))}</div>
    <label className="route-inline-input">
      <span>Свои минуты</span>
      <input type="number" min={15} max={1440} value={form.timeBudgetMinutes}
        onChange={(event) => onChange({ useTimeBudget: true, timeBudgetMinutes: event.target.value })} />
    </label>
    <div className="route-preset-row" aria-label="Время суток">{timeOfDayOptions.map((option) => (
      <button className={form.timeOfDay === option.value ? 'is-selected' : ''}
        type="button" key={option.label}
        onClick={() => onChange({ timeOfDay: option.value, routeTimeMode: routeTimeMode(option.value) })}>
        {option.label}
      </button>
    ))}</div>
  </section>
)
