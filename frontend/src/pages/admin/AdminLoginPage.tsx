import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ADMIN_LOGIN, ADMIN_PASSWORD } from './adminCredentials'
import { saveAdminSession } from './adminSession'
import './Admin.css'

export const AdminLoginPage = () => {
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (login === ADMIN_LOGIN && password === ADMIN_PASSWORD) {
      saveAdminSession()
      navigate('/admin/dashboard', { replace: true })
    } else {
      setError('Неверный логин или пароль')
    }
  }

  return (
    <div className="admin-login-screen">
      <div className="admin-login-box">
        <h1 className="admin-login-title">City Go Admin</h1>
        <form onSubmit={handleSubmit} className="admin-login-form">
          <label className="admin-field">
            <span>Логин</span>
            <input
              type="text"
              value={login}
              autoComplete="username"
              onChange={(e) => setLogin(e.target.value)}
              required
            />
          </label>
          <label className="admin-field">
            <span>Пароль</span>
            <input
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error && <p className="admin-login-error">{error}</p>}
          <button type="submit" className="admin-btn admin-btn-primary">Войти</button>
        </form>
        <p className="admin-login-note">Внутренняя административная панель City Go.</p>
      </div>
    </div>
  )
}
