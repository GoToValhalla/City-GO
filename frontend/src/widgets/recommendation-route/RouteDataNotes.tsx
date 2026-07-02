import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'

type Props = { route: RecommendationRouteResponse }

const looksLikeCode = (value: string): boolean => value.includes('_') && value === value.toLowerCase()

export const RouteDataNotes = ({ route }: Props) => {
  const notes = Array.from(new Set(route.explanation.data_notes ?? [])).filter((note) => !looksLikeCode(note)).slice(0, 4)
  if (!notes.length) return null
  return (
    <div className="route-data-notes">
      {notes.map((note) => <span key={note}>{note}</span>)}
    </div>
  )
}
