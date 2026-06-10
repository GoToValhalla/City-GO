export type EnrichmentBatchMeta = {
  batch_id: string
  status: string
  city_slug: string
  limit: number
  missing_fields: string[]
  only_published: boolean
  only_route_eligible: boolean
  export_csv_path: string
  enriched_csv_path: string
  import_preview_path: string
  import_result_path: string
  created_at: string
  total_exported: number
  by_city: Record<string, number>
  by_category: Record<string, number>
  missing_fields_breakdown: Record<string, number>
  next_action: string
}

export type EnrichmentExportMeta = {
  export_id: string
  batch_id?: string | null
  status?: string | null
  file_path: string
  export_csv_path?: string | null
  enriched_csv_path?: string | null
  city_slug?: string | null
  total_exported: number
  by_city: Record<string, number>
  by_category: Record<string, number>
  missing_fields_breakdown: Record<string, number>
  created_at: string
  next_action?: string | null
}

export type ImportPreviewResult = {
  batch_id: string
  rows_with_changes: number
  unsupported_fields: Record<string, number>
  errors: string[]
}

export type ImportApplyResult = {
  batch_id: string
  rows_updated: number
  fields_updated: Record<string, number>
  errors: string[]
}

export const QUICK_EXPORT_FIELDS = ['address', 'photo', 'description']
