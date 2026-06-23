import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './styles/responsive.css'
import './styles/home.css'
import './styles/places.css'
import './styles/discovery.css'
import './styles/cards.css'
import './styles/visuals.css'
import './styles/actions.css'
import './styles/place-ui.css'
import './styles/place-ui-skeleton.css'
import './styles/telegram-mini-app.css'
import { HomePage } from './pages/home/HomePage'
import { NearbyPage } from './pages/nearby/NearbyPage'
import { OpenNowPage } from './pages/open-now/OpenNowPage'
import { PlaceDetailPage } from './pages/places/PlaceDetailPage'
import { PlacesListPage } from './pages/places/PlacesListPage'
import { GenerateRoutePage } from './pages/routes/GenerateRoutePage'
import { RouteDetailPage } from './pages/routes/RouteDetailPage'
import { RoutesListPage } from './pages/routes/RoutesListPage'
import { WalkRoutePage } from './pages/routes/WalkRoutePage'
import { TelegramMapPage } from './pages/telegram/TelegramMapPage'
import { AdminLoginPage } from './pages/admin/AdminLoginPage'
import { AdminRouteGuard } from './pages/admin/AdminRouteGuard'
import { AdminLayout } from './pages/admin/AdminLayout'
import { AdminOverviewPage } from './pages/admin/AdminOverviewPage'
import { AdminCitiesPage } from './pages/admin/AdminCitiesPage'
import { AdminCityWorkspacePage } from './pages/admin/AdminCityWorkspacePage'
import { AdminPlacesPage } from './pages/admin/AdminPlacesPage'
import { AdminPlaceImagesPage } from './pages/admin/AdminPlaceImagesPage'
import { AdminPlaceVerificationsPage } from './pages/admin/AdminPlaceVerificationsPage'
import { AdminImportJobsPage } from './pages/admin/AdminImportJobsPage'
import { AdminCoveragePage } from './pages/admin/AdminCoveragePage'
import { AdminAuditLogPage } from './pages/admin/AdminAuditLogPage'
import { AdminPlaceEnrichmentPage } from './pages/admin/AdminPlaceEnrichmentPage'
import { AdminFeatureTogglesPage } from './pages/admin/AdminFeatureTogglesPage'
import { AdminMetricsPage } from './pages/admin/AdminMetricsPage'
import { AdminPlaceDetailPage } from './pages/admin/AdminPlaceDetailPage'
import { AdminPlaceCreatePage } from './pages/admin/AdminPlaceCreatePage'
import { AdminSystemLogsPage } from './pages/admin/AdminSystemLogsPage'
import { AdminRouteEligibilityPage } from './pages/admin/AdminRouteEligibilityPage'
import { AdminRouteDryRunPage } from './pages/admin/AdminRouteDryRunPage'
import { AdminRouteDataQualityPage } from './pages/admin/AdminRouteDataQualityPage'

function AdminPage({ children }: { children: React.ReactNode }) {
  return (
    <AdminRouteGuard>
      <AdminLayout>{children}</AdminLayout>
    </AdminRouteGuard>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/places" element={<PlacesListPage />} />
        <Route path="/places/:slug" element={<PlaceDetailPage />} />
        <Route path="/open-now" element={<OpenNowPage />} />
        <Route path="/nearby" element={<NearbyPage />} />
        <Route path="/routes" element={<RoutesListPage />} />
        <Route path="/routes/generate" element={<GenerateRoutePage />} />
        <Route path="/routes/:slug" element={<RouteDetailPage />} />
        <Route path="/walk-route" element={<WalkRoutePage />} />
        <Route path="/telegram/map" element={<TelegramMapPage />} />

        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route path="/admin" element={<Navigate to="/admin/overview" replace />} />
        <Route path="/admin/overview" element={<AdminPage><AdminOverviewPage /></AdminPage>} />
        <Route path="/admin/dashboard" element={<Navigate to="/admin/overview" replace />} />
        <Route path="/admin/cities" element={<AdminPage><AdminCitiesPage /></AdminPage>} />
        <Route path="/admin/cities/:slug" element={<AdminPage><AdminCityWorkspacePage /></AdminPage>} />
        <Route path="/admin/places" element={<AdminPage><AdminPlacesPage /></AdminPage>} />
        <Route path="/admin/places/new" element={<AdminPage><AdminPlaceCreatePage /></AdminPage>} />
        <Route path="/admin/places/:id" element={<AdminPage><AdminPlaceDetailPage /></AdminPage>} />
        <Route path="/admin/photos" element={<AdminPage><AdminPlaceImagesPage /></AdminPage>} />
        <Route path="/admin/place-images" element={<Navigate to="/admin/photos" replace />} />
        <Route path="/admin/verification" element={<AdminPage><AdminPlaceVerificationsPage /></AdminPage>} />
        <Route path="/admin/place-verifications" element={<Navigate to="/admin/verification" replace />} />
        <Route path="/admin/imports" element={<AdminPage><AdminImportJobsPage /></AdminPage>} />
        <Route path="/admin/import-jobs" element={<Navigate to="/admin/imports" replace />} />
        <Route path="/admin/coverage" element={<AdminPage><AdminCoveragePage /></AdminPage>} />
        <Route path="/admin/routes/eligibility" element={<AdminPage><AdminRouteEligibilityPage /></AdminPage>} />
        <Route path="/admin/routes/dry-run" element={<AdminPage><AdminRouteDryRunPage /></AdminPage>} />
        <Route path="/admin/routes/data-quality" element={<AdminPage><AdminRouteDataQualityPage /></AdminPage>} />
        <Route path="/admin/enrichment" element={<AdminPage><AdminPlaceEnrichmentPage /></AdminPage>} />
        <Route path="/admin/place-enrichment" element={<Navigate to="/admin/enrichment" replace />} />
        <Route path="/admin/features" element={<AdminPage><AdminFeatureTogglesPage /></AdminPage>} />
        <Route path="/admin/metrics" element={<AdminPage><AdminMetricsPage /></AdminPage>} />
        <Route path="/admin/audit" element={<AdminPage><AdminAuditLogPage /></AdminPage>} />
        <Route path="/admin/system-logs" element={<AdminPage><AdminSystemLogsPage /></AdminPage>} />
        <Route path="/admin/audit-log" element={<Navigate to="/admin/audit" replace />} />
        <Route path="/admin/photo-review" element={<Navigate to="/admin/photos" replace />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
