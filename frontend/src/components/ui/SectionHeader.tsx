import type { ReactNode } from 'react'

type SectionHeaderProps = {
  eyebrow?: string
  title: string
  description?: string
  right?: ReactNode
}

export const SectionHeader = ({
  eyebrow,
  title,
  description,
  right,
}: SectionHeaderProps) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        gap: '16px',
        flexWrap: 'wrap',
      }}
    >
      <div>
        {eyebrow ? (
          <div
            style={{
              fontSize: '13px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: '#64748b',
            }}
          >
            {eyebrow}
          </div>
        ) : null}

        <h2
          style={{
            margin: eyebrow ? '8px 0 0' : '0',
            fontSize: '42px',
            lineHeight: 0.98,
            letterSpacing: '-0.05em',
            fontWeight: 800,
            color: '#0f172a',
          }}
        >
          {title}
        </h2>

        {description ? (
          <p
            style={{
              marginTop: '10px',
              color: '#64748b',
              fontSize: '16px',
              lineHeight: 1.6,
              maxWidth: '760px',
            }}
          >
            {description}
          </p>
        ) : null}
      </div>

      {right ? <div>{right}</div> : null}
    </div>
  )
}
