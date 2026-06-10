const preview = [
  'Кофе в центре',
  'Прогулка у воды',
  'Ужин или вечерняя точка',
]

export const RouteHeroPreview = () => {
  return (
    <aside className="route-photo-preview" aria-label="Пример маршрута">
      <header>
        <span className="route-eyebrow">Пример</span>
        <strong>Кофе, море, ужин</strong>
      </header>
      <ol className="route-photo-stack">
        {preview.map((title, index) => (
          <li key={title}>
            <span>{index + 1}</span>
            <strong>{title}</strong>
          </li>
        ))}
      </ol>
    </aside>
  )
}
