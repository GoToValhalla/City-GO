import { Shuffle, Sparkles } from 'lucide-react'
import type { RandomRouteMode, RandomRoutePlan } from '../../features/routes/model/randomRoutePlan'

type Props = {
  budget: number
  categoriesCount: number
  mode: RandomRouteMode
  plan: RandomRoutePlan | null
  onBudgetChange: (minutes: number) => void
  onModeChange: (mode: RandomRouteMode) => void
}

export const RandomRouteModePicker = ({ budget, categoriesCount, mode, onBudgetChange, onModeChange, plan }: Props) => (
  <div className="route-random-config">
    <div aria-label="Режим случайного маршрута" className="route-random-modes" role="group">
      <button className={mode === 'random_places' ? 'is-active' : ''} onClick={() => onModeChange('random_places')} type="button">
        <span><Shuffle size={20} /></span><strong>Случайные места</strong><small>Вы задаёте время, CITY GO выбирает любые подходящие точки.</small>
      </button>
      <button className={mode === 'random_mood' ? 'is-active' : ''} onClick={() => onModeChange('random_mood')} type="button">
        <span><Sparkles size={20} /></span><strong>Случайное настроение</strong><small>Время и 1–3 категории выбираются заново при каждом запуске.</small>
      </button>
    </div>
    {mode === 'random_places' ? <label className="route-random-duration">Продолжительность
      <select value={budget} onChange={(event) => onBudgetChange(Number(event.target.value))}>
        {[60, 90, 120, 180, 240].map((minutes) => <option key={minutes} value={minutes}>{minutes} минут</option>)}
      </select>
    </label> : <p className="route-random-note">CITY GO выберет 1–3 из {categoriesCount} доступных категорий; параметры появятся вместе с маршрутом.</p>}
    {plan ? <p className="route-random-plan">Выбрано: {plan.minutes} минут · {plan.categories.length ? `${plan.categories.length} тем` : 'без фильтра по темам'}</p> : null}
  </div>
)
