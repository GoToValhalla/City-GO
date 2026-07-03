import { LocateFixed, MapPin, Sparkles, Wallet } from 'lucide-react'
import type { RecommendationRouteFormState } from '../../features/routes/model/recommendationRouteForm'
import { avoidedCategoryOptions, getInterestOptionsForFeatures } from './chipOptions'
import { RouteSlotBuilder } from './RouteSlotBuilder'
import { RouteTimeControls } from './RouteTimeControls'

type Props = {
  citySlug: string
  features: string[]
  form: RecommendationRouteFormState
  loading: boolean
  geoStatus: string | null
  geoError: string | null
  onUseCurrentLocation: () => void
  onUseCityCenter: () => void
  onChange: (patch: Partial<RecommendationRouteFormState>) => void
  onToggleInterest: (value: string) => void
  onToggleAvoided: (value: string) => void
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void
}

export const RouteRequestForm = ({ citySlug, features, form, loading, geoStatus, geoError, onUseCurrentLocation, onUseCityCenter, onChange, onToggleInterest, onToggleAvoided, onSubmit }: Props) => {
  const visibleInterestOptions = getInterestOptionsForFeatures(features)
  const hasSelectedInterests = form.interests.length > 0
  const slotCount = form.routeSlots?.length ?? 0

  return (
    <form className="route-form" onSubmit={onSubmit}>
      <div className="route-form-head"><p className="route-eyebrow">Конструктор прогулки</p><h2>Выбери время и старт</h2><p>City Go подберёт точки, порядок, длительность и честно покажет нюансы данных.</p></div>
      <RouteTimeControls form={form} onChange={onChange} />
      <section className="route-control-block" aria-label="Старт маршрута">
        <div className="route-control-title"><MapPin size={18} /><span>Откуда начать</span></div>
        <div className="route-chip-row"><button className={form.startSource === 'city_center' ? 'is-selected' : ''} type="button" onClick={onUseCityCenter}>От центра города</button><button className={form.startSource === 'current_location' ? 'is-selected' : ''} type="button" onClick={onUseCurrentLocation}>Использовать мою геолокацию</button><button className={form.startSource === 'address' ? 'is-selected' : ''} type="button" onClick={() => onChange({ startSource: 'address' })}>От адреса</button></div>
        {geoStatus ? <p className="route-start-note">{geoStatus}</p> : null}
        {geoError ? <p className="route-start-error">{geoError}</p> : null}
        {form.startSource === 'address' ? <label className="route-inline-input"><span>Адрес старта</span><input value={form.startAddress} placeholder="Например: Мира 1" onChange={(event) => onChange({ startAddress: event.target.value, startSource: 'address' })} /></label> : null}
        <p className="route-start-note">Координаты не нужно вводить руками: используем центр города, геолокацию браузера или адрес.</p>
        <p className="route-start-note">Текущий старт: {form.startSource || 'не выбран'} · {form.lat && form.lng ? `${form.lat}, ${form.lng}` : 'координаты не заданы'}</p>
      </section>
      <section className="route-control-block" aria-label="Интересы">
        <div className="route-control-title"><Sparkles size={18} /><span>Что хочется в маршруте</span></div>
        <p className="route-start-note route-interest-note">Это необязательно. Если ничего не выбрать, City Go всё равно соберёт обычную прогулку.</p>
        {!hasSelectedInterests ? <p className="route-start-note route-interest-fallback-note">Сейчас выбран авто-режим: маршрут строится как прогулка без узкой привязки к интересам.</p> : null}
        <div className="route-chip-row">{visibleInterestOptions.map((option) => <button className={form.interests.includes(option.value) ? 'is-selected' : ''} type="button" key={option.value} onClick={() => onToggleInterest(option.value)}>{option.label}</button>)}</div>
      </section>
      <RouteSlotBuilder citySlug={citySlug} form={form} loading={loading} onChange={onChange} />
      <section className="route-control-block" aria-label="Ограничения">
        <div className="route-control-title"><Wallet size={18} /><span>Ограничения и темп</span></div>
        <div className="route-field-grid"><select value={form.budgetLevel} onChange={(event) => onChange({ budgetLevel: event.target.value })}><option value="">Любой бюджет</option><option value="1">Бюджетно</option><option value="2">Средний бюджет</option><option value="3">Можно дороже</option></select><select value={form.paceMode} onChange={(event) => onChange({ paceMode: event.target.value })}><option value="">Обычный темп</option><option value="slow">Спокойнее</option><option value="fast">Быстрее</option></select></div>
        <div className="route-chip-row route-avoid-row">{avoidedCategoryOptions.map((option) => <button className={form.avoidedCategories.includes(option.value) ? 'is-selected' : ''} type="button" key={option.value} onClick={() => onToggleAvoided(option.value)}>Без: {option.label}</button>)}</div>
      </section>
      <details className="route-advanced"><summary><LocateFixed size={17} /> Техническая информация</summary><p className="route-start-note">Старт: {form.startSource || 'не выбран'}</p><p className="route-start-note">Координаты: {form.lat || '—'}, {form.lng || '—'}</p><p className="route-start-note">Режим: {slotCount ? 'constructor' : form.interests.length ? 'by_categories' : 'auto'}</p></details>
      <button className="route-primary-button" type="submit" disabled={loading}><Sparkles size={18} />{loading ? 'Собираю preview...' : slotCount ? 'Собрать маршрут по сценарию' : 'Собрать preview маршрута'}</button>
    </form>
  )
}
