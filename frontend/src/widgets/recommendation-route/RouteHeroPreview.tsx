import { getCurrentCity } from '../../shared/city/currentCity'

type CityRouteProfile = {
  title: string
  steps: string[]
}

const defaultProfile = (cityName: string, features: string[]): CityRouteProfile => features.includes('sea') ? ({
  title: 'Кофе, море, ужин',
  steps: [
    `Кофе в ${cityName}`,
    'Прогулка у воды',
    'Ужин или вечерняя точка',
  ],
}) : ({
  title: 'Кофе, прогулка, ужин',
  steps: [
    `Кофе в ${cityName}`,
    'Прогулка по центру',
    'Ужин или вечерняя точка',
  ],
})

const cityRouteProfiles: Record<string, CityRouteProfile> = {
  astrakhan: {
    title: 'Кофе, Волга, кремль',
    steps: [
      'Кофе в историческом центре',
      'Прогулка у Волги или канала',
      'Кремль, музей или вечерняя точка',
    ],
  },
  zelenogradsk: {
    title: 'Море, променад, кофе',
    steps: [
      'Променад у моря',
      'Кофе или десерт рядом',
      'Спокойная прогулка по городу',
    ],
  },
  kaliningrad: {
    title: 'Кафедральный, остров, кофе',
    steps: [
      'Кофе в центре',
      'Остров Канта или набережная',
      'Музей или вечерняя точка',
    ],
  },
  kutaisi: {
    title: 'Старый город, кофе, вид',
    steps: [
      'Кофе в центре',
      'Историческая точка',
      'Видовая или вечерняя остановка',
    ],
  },
  yerevan: {
    title: 'Кофе, каскад, вечер',
    steps: [
      'Кофе в центре',
      'Каскад или музей',
      'Вечерняя прогулка',
    ],
  },
}

type Props = {
  cityName?: string
  citySlug?: string
  features?: string[]
}

export const RouteHeroPreview = ({ cityName, citySlug, features }: Props) => {
  const currentCity = getCurrentCity()
  const effectiveSlug = citySlug ?? currentCity.slug
  const effectiveName = cityName ?? currentCity.name
  const profile = features ? defaultProfile(effectiveName, features) : (cityRouteProfiles[effectiveSlug] ?? defaultProfile(effectiveName, []))

  return (
    <aside className="route-photo-preview" aria-label="Пример маршрута">
      <header>
        <span className="route-eyebrow">Пример</span>
        <strong>{profile.title}</strong>
      </header>
      <ol className="route-photo-stack">
        {profile.steps.map((title, index) => (
          <li key={title}>
            <span>{index + 1}</span>
            <strong>{title}</strong>
          </li>
        ))}
      </ol>
    </aside>
  )
}
