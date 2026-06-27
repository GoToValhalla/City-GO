import { useState, type ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { clearAdminSession } from './adminSession'
import { AdminErrorBoundary } from './AdminErrorBoundary'
import { ADMIN_NAV_ITEMS, ADMIN_NAV_SECTION_LABELS } from './adminNavItems'
import './Admin.css'
import './AdminResponsive.css'

type Props = { children: ReactNode }

const navSections = Object.entries(
  ADMIN_NAV_ITEMS.reduce<Record<string, typeof ADMIN_NAV_ITEMS>>((acc, item) => {
    const section = item.section ?? 'main'
    acc[section] = [...(acc[section] ?? []), item]
    return acc
  }, {}),
)

export const AdminLayout = ({ children }: Props) => {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const logout = () => {
    clearAdminSession()
    navigate('/admin/login', { replace: true })
  }

  const closeMenu = () => setMenuOpen(false)

  return (
    <div className="admin-shell">
      <button type="button" className="admin-menu-toggle" onClick={() => setMenuOpen((v) => !v)} aria-label="Меню">
        ☰
      </button>
      {menuOpen && <button type="button" className="admin-overlay" aria-label="Закрыть меню" onClick={closeMenu} />}
      <aside className={`admin-sidebar ${menuOpen ? 'admin-sidebar-open' : ''}`}>
        <div className="admin-sidebar-title">City Go</div>
        <nav className="admin-nav">
          {navSections.map(([section, items]) => (
            <div key={section} className="admin-nav-section">
              <div className="admin-nav-section-title">{ADMIN_NAV_SECTION_LABELS[section] ?? section}</div>
              {items.map((item) => (
                <NavLink key={item.path} to={item.path} className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`} onClick={closeMenu}>
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>
      <div className="admin-main">
        <header className="admin-topbar">
          <span className="admin-topbar-label">Операционная панель</span>
          <button type="button" onClick={logout} className="admin-btn admin-btn-logout">Выйти</button>
        </header>
        <div className="admin-content"><AdminErrorBoundary>{children}</AdminErrorBoundary></div>
      </div>
    </div>
  )
}
