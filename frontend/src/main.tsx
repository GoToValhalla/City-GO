import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './styles/design-system.css'
import App from './App.tsx'
import { AppVersionBadge } from './shared/AppVersionBadge'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <div>
      <App />
      <AppVersionBadge />
    </div>
  </StrictMode>,
)
