const readBuildValue = (value: string | undefined, fallback: string): string => {
  const normalized = value?.trim()
  return normalized || fallback
}

const buildSha = readBuildValue(import.meta.env.VITE_BUILD_SHA, 'local')

export const frontendBuildInfo = {
  service: 'frontend',
  buildSha,
  buildShaShort: buildSha === 'local' ? 'local' : buildSha.slice(0, 7),
  buildRunId: readBuildValue(import.meta.env.VITE_BUILD_RUN_ID, 'local'),
  buildRunNumber: readBuildValue(import.meta.env.VITE_BUILD_RUN_NUMBER, 'local'),
  buildTime: readBuildValue(import.meta.env.VITE_BUILD_TIME, 'local'),
}
