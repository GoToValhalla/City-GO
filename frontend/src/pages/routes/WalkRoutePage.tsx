import { Navigate } from 'react-router-dom'

// Legacy-страница walk-route.
// Оставляем её, чтобы не ломать старые ссылки и кнопки.
// Фактически она просто перекидывает пользователя
// на универсальную detail-страницу маршрута по slug.
export const WalkRoutePage = () => {
  return <Navigate to="/routes/seaside-walk-zelenogradsk" replace />
}