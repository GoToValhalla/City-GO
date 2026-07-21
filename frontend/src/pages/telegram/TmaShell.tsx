import { Map, Route, Store } from 'lucide-react'
import { useCallback, type ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import { useTelegramBackButton } from '../../shared/telegram/useTelegramBackButton'
import { useTelegramMiniApp } from '../../shared/telegram/useTelegramMiniApp'
import { useTheme } from '../../shared/theme/useTheme'
import { useTmaEnabled } from './useTmaEnabled'

type Props = {
  title?: string
  onBack?: (() => void) | null
  cityChip?: ReactNode
  children: ReactNode
}

export const TmaShell = ({ children, cityChip, onBack = null, title }: Props) => {
  useTelegramMiniApp()
  useTheme()
  const navigate = useNavigate()
  const { enabled, error, loading } = useTmaEnabled()
  const goBack = useCallback(() => navigate(-1), [navigate])
  useTelegramBackButton(onBack ?? (window.history.length > 1 ? goBack : null))

  if (loading) return <div className="tma-shell app-screen"><div className="tma-content" role="status" aria-live="polite" aria-busy="true"><p>Загружаем приложение…</p><Skeleton /><Skeleton /></div></div>

  if (error) return <div className="tma-shell app-screen"><div className="tma-content">
    <ErrorState title="Не удалось загрузить приложение" description={error} retryLabel="Повторить" onRetry={() => window.location.reload()} />
  </div></div>

  if (!enabled) return <div className="tma-shell app-screen"><div className="tma-content">
    <div className="tma-disabled-screen">
      <EmptyState title="Приложение временно недоступно" description="Мини-приложение City GO сейчас выключено администратором. Загляните позже." />
    </div>
  </div></div>

  return <div className="tma-shell app-screen">
    {title || cityChip ? <header className="tma-header">{title ? <h1>{title}</h1> : <span />}{cityChip}</header> : null}
    <main className="tma-content">{children}</main>
    <nav className="tma-tabbar" aria-label="Навигация">
      <NavLink to="/telegram/places" className={({ isActive }) => isActive ? 'active' : ''}><Store size={20} /><span>Места</span></NavLink>
      <NavLink to="/telegram/route" className={({ isActive }) => isActive ? 'active' : ''}><Route size={20} /><span>Маршрут</span></NavLink>
      <NavLink to="/telegram" end className={({ isActive }) => isActive ? 'active' : ''}><Map size={20} /><span>Город</span></NavLink>
    </nav>
  </div>
}
