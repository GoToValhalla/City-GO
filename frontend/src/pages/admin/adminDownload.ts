import { requireAdminApiToken } from './adminToken'
import { toAdminErrorMessage } from './shared/adminErrorMessage'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

const filenameFromDisposition = (value: string | null): string | null => {
  if (!value) return null
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1].replace(/"/g, ''))
  const plainMatch = value.match(/filename="?([^";]+)"?/i)
  return plainMatch?.[1] ?? null
}

export const adminDownload = async (path: string, fallbackFilename: string): Promise<void> => {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      Authorization: `Bearer ${requireAdminApiToken()}`,
    },
  })

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText)
    throw new Error(toAdminErrorMessage(response.status, text))
  }

  const blob = await response.blob()
  const filename = filenameFromDisposition(response.headers.get('content-disposition')) ?? fallbackFilename
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
