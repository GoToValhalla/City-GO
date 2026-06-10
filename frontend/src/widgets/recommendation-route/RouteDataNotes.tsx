import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'

type Props = { route: RecommendationRouteResponse }

export const RouteDataNotes = ({ route }: Props) => {
  const notes = route.explanation.data_notes ?? []
  if (!notes.length) return null
  return (
    <div className="route-data-notes">
      {notes.map((note) => <span key={note}>{note}</span>)}
    </div>
  )
}
