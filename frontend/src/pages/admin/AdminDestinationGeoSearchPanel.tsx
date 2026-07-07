import { type FormEvent, useState } from 'react'
import { flushSync } from 'react-dom'
import { AdminApiError } from './adminApi'
import {
  DESTINATION_TYPE_LABELS,
  createDestinationFromGeoCandidate,
  createScopeFromGeoCandidate,
  formatCandidateBbox,
  searchDestinationGeo,
  suggestDestinationSlug,
  type DestinationGeoCandidate,
} from './destinationGeoApi'

type Props = {
  mode: 'create-destination' | 'create-scope'
  destinationSlug?: string
  onDestinationCreated?: (slug: string) => void
  onScopeApplied?: (action: string) => void
}

export const AdminDestinationGeoSearchPanel = ({
  mode,
  destinationSlug,
  onDestinationCreated,
  onScopeApplied,
}: Props) => {
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [actingKey, setActingKey] = useState<string | null>(null)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [items, setItems] = useState<DestinationGeoCandidate[]>([])
  const [searched, setSearched] = useState(false)
  const [scopeCode, setScopeCode] = useState('catalog-core')
  const [scopeName, setScopeName] = useState('')
  const [recoverExisting, setRecoverExisting] = useState(false)

  const onSearch = async (event: FormEvent) => {
    event.preventDefault()
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setSearchError('Введите минимум 2 символа')
      return
    }
    setSearching(true)
    setSearchError(null)
    setActionError(null)
    setNotice(null)
    try {
      const data = await searchDestinationGeo(trimmed)
      setItems(data.items)
      setSearched(true)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Не удалось выполнить геопоиск'
      flushSync(() => {
        setItems([])
        setSearched(true)
        setSearchError(message)
      })
    } finally {
      setSearching(false)
    }
  }

  const createDestination = async (candidate: DestinationGeoCandidate) => {
    setActingKey(candidate.candidate_key)
    setActionError(null)
    setNotice(null)
    try {
      const created = await createDestinationFromGeoCandidate(candidate, {
        slug: suggestDestinationSlug(candidate.title),
        name: candidate.title,
        destination_type: candidate.destination_type,
      })
      setNotice(`Направление «${created.slug}» создано`)
      onDestinationCreated?.(created.slug)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Не удалось создать направление')
    } finally {
      setActingKey(null)
    }
  }

  const applyScope = async (candidate: DestinationGeoCandidate) => {
    if (!destinationSlug) return
    setActingKey(candidate.candidate_key)
    setActionError(null)
    setNotice(null)
    const body = {
      code: scopeCode.trim() || suggestDestinationSlug(candidate.title),
      name: scopeName.trim() || candidate.title,
      recover: recoverExisting,
    }
    try {
      const result = await createScopeFromGeoCandidate(destinationSlug, candidate, body)
      const label = result.action === 'recovered' ? 'Контур обновлён' : 'Контур добавлен'
      setNotice(label)
      onScopeApplied?.(result.action)
    } catch (err) {
      if (err instanceof AdminApiError && err.status === 409 && !recoverExisting) {
        setActionError('Контур с таким кодом уже существует. Включите обновление, чтобы перезаписать его.')
      } else {
        setActionError(err instanceof Error ? err.message : 'Не удалось добавить контур')
      }
    } finally {
      setActingKey(null)
    }
  }

  return (
    <section className="admin-section" data-testid="destination-geo-search">
      <h2 className="admin-section-title">
        {mode === 'create-destination' ? 'Найти направление на карте' : 'Добавить контур по геопоиску'}
      </h2>
      <form className="admin-form-grid admin-form-inline" onSubmit={(event) => void onSearch(event)}>
        <label className="admin-field admin-field-grow">
          <span>Город или регион</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Например, Куршская коса"
            disabled={searching || Boolean(actingKey)}
          />
        </label>
        <button type="submit" className="admin-btn admin-btn-safe" disabled={searching || Boolean(actingKey)}>
          {searching ? 'Поиск…' : 'Найти'}
        </button>
      </form>

      {mode === 'create-scope' ? (
        <div className="admin-form-grid">
          <label className="admin-field"><span>Код контура</span><input value={scopeCode} onChange={(e) => setScopeCode(e.target.value)} disabled={Boolean(actingKey)} /></label>
          <label className="admin-field"><span>Название контура</span><input value={scopeName} onChange={(e) => setScopeName(e.target.value)} placeholder="По умолчанию — из кандидата" disabled={Boolean(actingKey)} /></label>
          <label className="admin-field admin-checkbox-field">
            <input type="checkbox" checked={recoverExisting} onChange={(e) => setRecoverExisting(e.target.checked)} disabled={Boolean(actingKey)} />
            Обновить существующий контур с этим кодом (перезапишет bbox и название)
          </label>
        </div>
      ) : null}

      {searchError ? <div className="admin-state admin-state-error">{searchError}</div> : null}
      {actionError ? <div className="admin-state admin-state-error">{actionError}</div> : null}
      {notice ? <div className="admin-state admin-state-success">{notice}</div> : null}

      {searched && !items.length && !searchError ? (
        <p className="admin-empty-state" data-testid="geo-search-empty">Ничего не найдено. Уточните запрос.</p>
      ) : null}

      {items.length ? (
        <ul className="admin-geo-candidate-list" data-testid="geo-candidate-list">
          {items.map((candidate) => (
            <li key={candidate.candidate_key} className="admin-geo-candidate-card" data-testid="geo-candidate-item">
              <div>
                <strong>{candidate.title}</strong>
                {candidate.display_name ? <p className="admin-page-subtitle">{candidate.display_name}</p> : null}
                <p className="admin-page-subtitle">
                  {DESTINATION_TYPE_LABELS[candidate.destination_type] ?? candidate.destination_type}
                  {' · '}
                  {candidate.lat.toFixed(4)}, {candidate.lng.toFixed(4)}
                  {formatCandidateBbox(candidate.bbox) ? ` · ${formatCandidateBbox(candidate.bbox)}` : ''}
                </p>
              </div>
              <button
                type="button"
                className="admin-btn admin-btn-safe"
                disabled={Boolean(actingKey) || searching}
                onClick={() => void (mode === 'create-destination' ? createDestination(candidate) : applyScope(candidate))}
              >
                {actingKey === candidate.candidate_key
                  ? 'Сохранение…'
                  : mode === 'create-destination'
                    ? 'Создать направление'
                    : 'Добавить контур'}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
