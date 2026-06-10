import { useState, type ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { clearAdminSession } from './adminSession'
import { ADMIN_NAV_ITEMS } from './adminNavItems'
import './Admin.css'
import './AdminResponsive.css'

type Props = { children: ReactNode }

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
          {ADMIN_NAV_ITEMS.map((item) => (
            <NavLink key={item.path} to={item.path} className={({ isActive }) => `admin-nav-link${isActive ? ' active' : ''}`} onClick={closeMenu}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="admin-main">
        <header className="admin-topbar">
          <span className="admin-topbar-label">Операционная панель</span>
          <button type="button" onClick={logout} className="admin-btn admin-btn-logout">Выйти</button>
        </header>
        <div className="admin-content">{children}</div>
      </div>
    </div>
  )
}
