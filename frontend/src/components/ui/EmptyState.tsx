import { SurfaceCard } from './SurfaceCard'

type EmptyStateProps = {
  message: string
}

export const EmptyState = ({ message }: EmptyStateProps) => {
  return (
    <SurfaceCard
      style={{
        background: '#ffffff',
        border: '1px dashed #cbd5e1',
        color: '#475569',
        padding: '20px',
      }}
    >
      {message}
    </SurfaceCard>
  )
}
