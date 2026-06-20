import { frontendBuildInfo } from './config/buildInfo'

export function AppVersionBadge() {
  return <div className="app-version-badge">FE {frontendBuildInfo.buildShaShort} BE /api/version</div>
}
