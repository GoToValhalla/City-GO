import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { AppVersionBadge } from './shared/AppVersionBadge'
import './styles/design-system.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <div>
      <App />
      <AppVersionBadge />
    </div>
  </StrictMode>,
)
