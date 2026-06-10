type Toggle = {
  key: string
  label?: string | null
  description?: string | null
  value_bool: boolean
  default?: boolean | null
  group?: string | null
  updated_by?: string | null
  updated_at?: string | null
}

type Props = { item: Toggle; busy: string | null; onToggle: (key: string, next: boolean) => void }

const fmt = (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleString('ru-RU') : null)

export const AdminFeatureToggleRow = ({ item, busy, onToggle }: Props) => (
  <label className="admin-toggle-row">
    <input
      type="checkbox"
      checked={item.value_bool}
      disabled={busy === item.key}
      onChange={(e) => onToggle(item.key, e.target.checked)}
    />
    <span>
      <strong>{item.label ?? item.key}</strong>
      {item.description && <span className="admin-muted"> — {item.description}</span>}
      <div className="admin-muted">
        По умолчанию: {item.default ? 'вкл' : 'выкл'}
        {item.updated_by && ` · ${item.updated_by}`}
        {fmt(item.updated_at) && ` · ${fmt(item.updated_at)}`}
      </div>
    </span>
  </label>
)
