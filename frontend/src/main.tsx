import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'maplibre-gl/dist/maplibre-gl.css'
import './index.css'
import './styles/design-system.css'
import './styles/maplibre.css'
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
