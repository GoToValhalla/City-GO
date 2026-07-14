import { Laptop, Moon, Sun } from 'lucide-react'
import type { ThemeMode } from '../../shared/theme/themeStorage'

const OPTIONS: { mode: ThemeMode; label: string; icon: typeof Sun }[] = [
  { mode: 'system', label: 'Системная', icon: Laptop },
  { mode: 'light', label: 'Светлая', icon: Sun },
  { mode: 'dark', label: 'Тёмная', icon: Moon },
]

type Props = {
  mode: ThemeMode
  onChange: (mode: ThemeMode) => void
  className?: string
}

export const ThemeToggle = ({ className, mode, onChange }: Props) => (
  <div aria-label="Тема оформления" className={className ? `theme-toggle ${className}` : 'theme-toggle'} role="radiogroup">
    {OPTIONS.map(({ icon: Icon, label, mode: optionMode }) => (
      <button
        aria-checked={mode === optionMode}
        aria-label={label}
        className={mode === optionMode ? 'is-active' : ''}
        key={optionMode}
        onClick={() => onChange(optionMode)}
        role="radio"
        type="button"
      >
        <Icon size={16} />
      </button>
    ))}
  </div>
)
