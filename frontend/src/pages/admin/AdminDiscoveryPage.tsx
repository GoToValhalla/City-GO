import { type FormEvent, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AdminDestinationGeoSearchPanel } from './AdminDestinationGeoSearchPanel'
import {
  bulkCreateDiscovery,
  discoverRegion,
  searchDiscoveryRegions,
  type DiscoveryCandidate,
  type DiscoveryPreview,
  type RegionCandidate,
} from './discoveryApi'
import './AdminDataPipeline.css'

type TabId = 'region' | 'city' | 'advanced'

const TIER_LABELS: Record<string, string> = {
  top: 'Топ', high: 'Высокий', medium: 'Средний', low: 'Низкий', unknown: 'Неизвестно',
}

export const AdminDiscoveryPage = () => {
  const [tab, setTab] = useState<TabId>('region')
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [discovering, setDiscovering] = useState(false)
  const [creating, setCreating] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [regions, setRegions] = useState<RegionCandidate[]>([])
  const [selectedRegion, setSelectedRegion] = useState<RegionCandidate | null>(null)
  const [preview, setPreview] = useState<DiscoveryPreview | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [showExisting, setShowExisting] = useState(true)
  const [warningsOnly, setWarningsOnly] = useState(false)
  const [updateScopes, setUpdateScopes] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [resultSummary, setResultSummary] = useState<string | null>(null)

  const visibleCandidates = useMemo(() => {
    const items = preview?.candidates ?? []
    return items.filter((item) => {
      if (!showExisting && item.existing_match) return false
      if (warningsOnly && !item.warnings.length) return false
      return true
    })
  }, [preview, showExisting, warningsOnly])

  const onRegionSearch = async (event: FormEvent) => {
    event.preventDefault()
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setSearchError('Введите минимум 2 символа')
      return
    }
    setSearching(true)
    setSearchError(null)
    setActionError(null)
    setResultSummary(null)
    try {
      const data = await searchDiscoveryRegions(trimmed)
      setRegions(data.items)
      setSelectedRegion(null)
      setPreview(null)
    } catch (err) {
      setRegions([])
      setSearchError(err instanceof Error ? err.message : 'Не удалось найти регион')
    } finally {
      setSearching(false)
    }
  }

  const onDiscover = async (region: RegionCandidate) => {
    setSelectedRegion(region)
    setDiscovering(true)
    setActionError(null)
    setResultSummary(null)
    setSelectedIds(new Set())
    try {
      const data = await discoverRegion(region.id)
      setJobId(data.job.id)
      setPreview(data.preview)
    } catch (err) {
      setPreview(null)
      setActionError(err instanceof Error ? err.message : 'Не удалось запустить discovery')
    } finally {
      setDiscovering(false)
    }
  }

  const toggleCandidate = (id: string) => {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectTier = (tier: string) => {
    const ids = (preview?.candidates ?? []).filter((c) => c.tier === tier).map((c) => c.id)
    setSelectedIds(new Set(ids))
  }

  const onBulkCreate = async () => {
    if (!jobId || !selectedIds.size) return
    setCreating(true)
    setActionError(null)
    try {
      const result = await bulkCreateDiscovery(jobId, [...selectedIds], { update_existing_scopes: updateScopes })
      setResultSummary(`Создано: ${result.created}, пропущено: ${result.skipped_existing}, конфликтов: ${result.conflicts}, ошибок: ${result.errors}`)
      setConfirmOpen(false)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Не удалось создать направления')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="admin-data-pipeline" data-testid="admin-discovery-page">
      <header className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Центр открытия направлений</h1>
          <p className="admin-page-subtitle">Сначала выберите регион — система предложит туристические направления и контуры.</p>
        </div>
        <Link className="admin-btn" to="/admin/destinations">Список направлений</Link>
      </header>

      <nav className="admin-action-row" data-testid="discovery-tabs">
        <button type="button" className={`admin-btn ${tab === 'region' ? 'admin-btn-safe' : 'admin-btn-muted'}`} onClick={() => setTab('region')}>По региону</button>
        <button type="button" className={`admin-btn ${tab === 'city' ? 'admin-btn-safe' : 'admin-btn-muted'}`} onClick={() => setTab('city')}>Поиск города</button>
        <button type="button" className={`admin-btn ${tab === 'advanced' ? 'admin-btn-safe' : 'admin-btn-muted'}`} onClick={() => setTab('advanced')}>Расширенные инструменты</button>
      </nav>

      {tab === 'region' ? (
        <>
          <section className="admin-section" data-testid="discovery-region-search">
            <h2 className="admin-section-title">1. Найти регион или страну</h2>
            <form className="admin-form-grid admin-form-inline" onSubmit={(event) => void onRegionSearch(event)}>
              <label className="admin-field admin-field-grow">
                <span>Регион / страна</span>
                <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Калининградская область" disabled={searching || discovering} />
              </label>
              <button type="submit" className="admin-btn admin-btn-safe" disabled={searching || discovering}>{searching ? 'Поиск…' : 'Найти регион'}</button>
            </form>
            {searchError ? <div className="admin-state admin-state-error">{searchError}</div> : null}
            {regions.length ? (
              <ul className="admin-geo-candidate-list" data-testid="discovery-region-list">
                {regions.map((region) => (
                  <li key={region.id} className="admin-geo-candidate-card">
                    <div>
                      <strong>{region.name}</strong>
                      {region.english_name ? <p className="admin-page-subtitle">{region.english_name} · {region.country}</p> : null}
                      <p className="admin-page-subtitle">{region.type} · {region.provider}</p>
                    </div>
                    <button type="button" className="admin-btn admin-btn-safe" disabled={discovering} onClick={() => void onDiscover(region)}>
                      {discovering && selectedRegion?.id === region.id ? 'Анализ…' : 'Показать кандидаты'}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>

          {preview ? (
            <section className="admin-section" data-testid="discovery-proposals">
              <h2 className="admin-section-title">2. Предложения для {preview.region.name}</h2>
              {preview.warnings.map((warning) => <div key={warning.code} className="admin-state admin-state-warning">{warning.message}</div>)}
              <div className="admin-action-row">
                <button type="button" className="admin-btn admin-btn-muted" onClick={() => selectTier('top')}>Выбрать top</button>
                <button type="button" className="admin-btn admin-btn-muted" onClick={() => selectTier('high')}>Выбрать high</button>
                <label className="admin-field admin-checkbox-field"><input type="checkbox" checked={showExisting} onChange={(e) => setShowExisting(e.target.checked)} /> Показывать существующие</label>
                <label className="admin-field admin-checkbox-field"><input type="checkbox" checked={warningsOnly} onChange={(e) => setWarningsOnly(e.target.checked)} /> Только с предупреждениями</label>
              </div>
              <div className="admin-table-wrap">
                <table className="admin-table" data-testid="discovery-candidate-table">
                  <thead><tr><th /><th>Название</th><th>Тип</th><th>Tier</th><th>Confidence</th><th>Предупреждения</th><th>Существует</th><th>Контуры</th></tr></thead>
                  <tbody>
                    {visibleCandidates.map((item) => (
                      <CandidateRow key={item.id} item={item} checked={selectedIds.has(item.id)} onToggle={() => toggleCandidate(item.id)} />
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="admin-action-row">
                <button type="button" className="admin-btn admin-btn-safe" disabled={!selectedIds.size} onClick={() => setConfirmOpen(true)}>Создать выбранные ({selectedIds.size})</button>
              </div>
              {confirmOpen ? (
                <div className="admin-section" data-testid="discovery-bulk-confirm">
                  <p>Подтвердите создание {selectedIds.size} направлений с рекомендованными контурами.</p>
                  <label className="admin-field admin-checkbox-field">
                    <input type="checkbox" checked={updateScopes} onChange={(e) => setUpdateScopes(e.target.checked)} />
                    Обновить существующие контуры с тем же кодом (перезапишет bbox и название)
                  </label>
                  <div className="admin-action-row">
                    <button type="button" className="admin-btn admin-btn-safe" disabled={creating} onClick={() => void onBulkCreate()}>{creating ? 'Создание…' : 'Подтвердить создание'}</button>
                    <button type="button" className="admin-btn admin-btn-muted" onClick={() => setConfirmOpen(false)}>Отмена</button>
                  </div>
                </div>
              ) : null}
              {resultSummary ? <div className="admin-state admin-state-success" data-testid="discovery-result-summary">{resultSummary}</div> : null}
            </section>
          ) : null}
        </>
      ) : null}

      {tab === 'city' ? (
        <AdminDestinationGeoSearchPanel mode="create-destination" onDestinationCreated={(slug) => { window.location.href = `/admin/destinations/${slug}` }} />
      ) : null}

      {tab === 'advanced' ? (
        <section className="admin-section" data-testid="discovery-advanced">
          <h2 className="admin-section-title">Расширенные инструменты</h2>
          <p className="admin-page-subtitle">Ручной ввод bbox, кодов контуров и восстановление — только на странице конкретного направления.</p>
          <Link className="admin-btn" to="/admin/destinations">Открыть список направлений</Link>
        </section>
      ) : null}

      {actionError ? <div className="admin-state admin-state-error">{actionError}</div> : null}
    </div>
  )
}

const CandidateRow = ({ item, checked, onToggle }: { item: DiscoveryCandidate; checked: boolean; onToggle: () => void }) => (
  <tr data-testid="discovery-candidate-row">
    <td><input type="checkbox" checked={checked} onChange={onToggle} aria-label={`Выбрать ${item.name}`} /></td>
    <td>{item.name}{item.english_name ? <div className="admin-page-subtitle">{item.english_name}</div> : null}</td>
    <td>{item.type}</td>
    <td><span data-testid="discovery-tier">{TIER_LABELS[item.tier] ?? item.tier}</span></td>
    <td><span data-testid="discovery-confidence">{item.confidence.overall ?? '—'}</span></td>
    <td>{item.warnings.length ? item.warnings.map((w) => w.code).join(', ') : '—'}</td>
    <td>{item.existing_match ? <span data-testid="discovery-existing-badge">{item.existing_match.slug}</span> : '—'}</td>
    <td>{item.recommended_scopes.map((s) => s.code).join(', ') || '—'}</td>
  </tr>
)
