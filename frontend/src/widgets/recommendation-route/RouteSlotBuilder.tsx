import { useState } from 'react'
import { ListPlus, RefreshCw, Trash2 } from 'lucide-react'
import { buildStructuredRouteOptions } from '../../api/recommendations/recommendationRoute.api'
import type { RouteBuilderSlot, UserRouteSlotOptions } from '../../api/recommendations/recommendationRoute.types'
import { buildRecommendationRouteRequest, type RecommendationRouteFormState } from '../../features/routes/model/recommendationRouteForm'
import { categoryLabel } from '../../shared/place/categoryLabels'

type Props = {
  citySlug: string
  form: RecommendationRouteFormState
  loading: boolean
  onChange: (patch: Partial<RecommendationRouteFormState>) => void
}

const SLOT_TYPES = [
  'cafe',
  'park',
  'museum',
  'food',
  'viewpoint',
  'landmark',
  'history',
  'culture',
  'walk',
]

const defaultSlot = (index: number): RouteBuilderSlot => ({
  slot_id: `slot-${Date.now()}-${index}`,
  category: SLOT_TYPES[index % SLOT_TYPES.length],
  type: SLOT_TYPES[index % SLOT_TYPES.length],
  required: true,
  duration: null,
  selected_place_id: null,
  min_count: 1,
  max_count: 1,
})

export const RouteSlotBuilder = ({ citySlug, form, loading, onChange }: Props) => {
  const [slotOptions, setSlotOptions] = useState<Record<string, UserRouteSlotOptions>>({})
  const [status, setStatus] = useState<string | null>(null)
  const slots = form.routeSlots

  const patchSlot = (slotId: string, patch: Partial<RouteBuilderSlot>) => {
    onChange({
      buildMode: 'constructor',
      routeSlots: slots.map((slot) => (slot.slot_id === slotId ? { ...slot, ...patch } : slot)),
    })
  }

  const addSlot = () => {
    onChange({ buildMode: 'constructor', routeSlots: [...slots, defaultSlot(slots.length)] })
  }

  const removeSlot = (slotId: string) => {
    onChange({ routeSlots: slots.filter((slot) => slot.slot_id !== slotId), buildMode: slots.length <= 1 ? 'auto' : 'constructor' })
    setSlotOptions((current) => {
      const next = { ...current }
      delete next[slotId]
      return next
    })
  }

  const loadOptions = async () => {
    const payload = buildRecommendationRouteRequest({ ...form, buildMode: 'constructor' }, citySlug)
    if (!payload.ok) {
      setStatus(payload.error)
      return
    }
    try {
      setStatus('Подбираю места для слотов...')
      const response = await buildStructuredRouteOptions(payload.value)
      setSlotOptions(Object.fromEntries(response.slots.map((slot) => [slot.slot_id, slot])))
      setStatus(response.slots.some((slot) => slot.options.length === 0) ? 'Часть слотов пока без вариантов.' : 'Варианты подобраны.')
    } catch (error) {
      console.error(error)
      setStatus('Не удалось подобрать места для слотов.')
    }
  }

  return (
    <section className="route-control-block route-slot-builder" aria-label="Ручной сценарий прогулки">
      <div className="route-control-title">
        <ListPlus size={18} />
        <span>Сценарий прогулки из слотов</span>
      </div>
      <p className="route-start-note">Собери порядок прогулки сам: например кофе → парк → музей → еда → видовая точка.</p>
      <div className="route-chip-row">
        <button type="button" className={slots.length ? 'is-selected' : ''} onClick={addSlot} disabled={loading || slots.length >= 8}>
          Добавить слот
        </button>
        {slots.length ? <button type="button" onClick={() => void loadOptions()} disabled={loading}>Подобрать места</button> : null}
        {slots.length ? <button type="button" onClick={() => onChange({ routeSlots: [], buildMode: 'auto' })} disabled={loading}>Очистить сценарий</button> : null}
      </div>
      {slots.length ? (
        <div className="route-slot-list">
          {slots.map((slot, index) => {
            const slotId = slot.slot_id ?? `slot-${index + 1}`
            const options = slotOptions[slotId]?.options ?? []
            const selected = options.find((option) => option.place_id === slot.selected_place_id)
            return (
              <article className="route-slot-card" key={slotId}>
                <div className="route-slot-head">
                  <strong>{index + 1}. {categoryLabel(slot.category || slot.type || '')}</strong>
                  <button type="button" onClick={() => removeSlot(slotId)} disabled={loading}><Trash2 size={14} /> Удалить</button>
                </div>
                <div className="route-field-grid">
                  <select value={slot.category || slot.type || ''} onChange={(event) => patchSlot(slotId, { category: event.target.value, type: event.target.value, selected_place_id: null })}>
                    {SLOT_TYPES.map((type) => <option value={type} key={type}>{categoryLabel(type)}</option>)}
                  </select>
                  <select value={slot.duration ?? ''} onChange={(event) => patchSlot(slotId, { duration: event.target.value ? Number(event.target.value) : null })}>
                    <option value="">Обычная длительность</option>
                    <option value="15">15 минут</option>
                    <option value="30">30 минут</option>
                    <option value="45">45 минут</option>
                    <option value="60">60 минут</option>
                  </select>
                </div>
                <label className="route-slot-checkbox"><input type="checkbox" checked={slot.required !== false} onChange={(event) => patchSlot(slotId, { required: event.target.checked })} /> обязательный слот</label>
                {selected ? <p className="route-start-note">Выбрано: <strong>{selected.title}</strong></p> : null}
                {options.length ? (
                  <div className="route-slot-options">
                    {options.map((option) => (
                      <button type="button" className={slot.selected_place_id === option.place_id ? 'is-selected' : ''} key={option.place_id} onClick={() => patchSlot(slotId, { selected_place_id: option.place_id })}>
                        <span>{option.title}</span>
                        <small>{option.walk_minutes ? `${option.walk_minutes} мин пешком` : option.address || categoryLabel(option.category)}</small>
                      </button>
                    ))}
                    <button type="button" onClick={() => patchSlot(slotId, { selected_place_id: null })}><RefreshCw size={14} /> Заменить выбор</button>
                  </div>
                ) : null}
              </article>
            )
          })}
        </div>
      ) : null}
      {status ? <p className="route-start-note">{status}</p> : null}
    </section>
  )
}
