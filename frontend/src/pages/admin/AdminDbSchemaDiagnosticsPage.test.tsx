/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminDbSchemaDiagnosticsPage } from './AdminDbSchemaDiagnosticsPage'

const mockAdminGet = vi.fn()

vi.mock('./adminApi', () => ({
  adminGet: (...args: unknown[]) => mockAdminGet(...args),
}))

const okPayload = {
  status: 'ok',
  alembic_version: 'a1c2d3e4f5b6',
  checked_at: '2026-07-07T20:00:00+00:00',
  contracts: {
    import_critical: {
      status: 'ok',
      missing_tables: [],
      missing_columns: [],
      existing_tables: ['places'],
      existing_columns: ['places.id'],
      extra_info: {},
    },
    photo_critical: { status: 'ok', missing_tables: [], missing_columns: [], existing_tables: [], existing_columns: [], extra_info: {} },
    route_critical: { status: 'ok', missing_tables: [], missing_columns: [], existing_tables: [], existing_columns: [], extra_info: {} },
  },
  raw_summary: { tables_checked: 40, columns_checked: 120, missing_total: 0 },
}

const driftPayload = {
  ...okPayload,
  status: 'schema_drift',
  contracts: {
    ...okPayload.contracts,
    import_critical: {
      status: 'schema_drift',
      missing_tables: ['place_field_provenance'],
      missing_columns: ['places.place_layer', 'places.route_policy'],
      existing_tables: ['places'],
      existing_columns: ['places.id'],
      extra_info: {},
    },
  },
  raw_summary: { tables_checked: 40, columns_checked: 120, missing_total: 3 },
}

describe('AdminDbSchemaDiagnosticsPage', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders drift state with missing tables and columns', async () => {
    mockAdminGet.mockResolvedValueOnce(driftPayload)
    render(<MemoryRouter><AdminDbSchemaDiagnosticsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Есть расхождения')).toBeInTheDocument())
    expect(screen.getByText('place_field_provenance')).toBeInTheDocument()
    expect(screen.getByText('places.place_layer')).toBeInTheDocument()
    expect(screen.getByTestId('admin-db-schema-page').textContent).toContain('a1c2d3e4f5b6')
  })

  it('renders ok state', async () => {
    mockAdminGet.mockResolvedValueOnce(okPayload)
    render(<MemoryRouter><AdminDbSchemaDiagnosticsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Схема соответствует контракту')).toBeInTheDocument())
  })

  it('renders copyable JSON report', async () => {
    mockAdminGet.mockResolvedValueOnce(driftPayload)
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })
    render(<MemoryRouter><AdminDbSchemaDiagnosticsPage /></MemoryRouter>)
    await screen.findByText('Есть расхождения')
    fireEvent.click(screen.getByRole('button', { name: 'Скопировать отчёт' }))
    await waitFor(() => expect(writeText).toHaveBeenCalled())
    expect(String(writeText.mock.calls[0][0])).toContain('schema_drift')
  })
})
