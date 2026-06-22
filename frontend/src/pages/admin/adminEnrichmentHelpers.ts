export const batchFilePath = (batchId: string, file: string) =>
  `/admin/place-enrichment/batches/${batchId}/files/${file}`

export const STATUS_LABEL: Record<string, string> = {
  exported: 'Экспортирован',
  enriched: 'Обогащён',
  previewed: 'Preview готов',
  imported: 'Импортирован',
  failed: 'Ошибка',
}