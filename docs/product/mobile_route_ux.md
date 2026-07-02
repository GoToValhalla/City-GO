# CITYGO-161 · Mobile Route UX

## Реализовано

- Форма построения маршрута после успешной сборки сворачивается в compact details на странице `frontend/src/pages/routes/GenerateRoutePage.tsx`.
- Первый экран результата теперь показывает главное: статус, количество мест, время, расстояние, качество и основные CTA.
- Основные CTA находятся в `RouteResultPanel`: `Пересобрать`, `Добавить место`, `Заменить точку`, `Начать маршрут`.
- Предупреждения маршрута свернуты в блок `Есть нюансы данных` без raw technical codes: `frontend/src/widgets/recommendation-route/RouteWarnings.tsx`.
- Доступные candidate options спрятаны под accordion `Добавить место` и ограничены шестью карточками: `RouteCandidateOptions.tsx`.
- Карточки точек маршрута сокращены до названия, категории, адреса, времени визита, критичного предупреждения и действий: `RoutePointList.tsx`.
- Уменьшена визуальная нагрузка мобильного результата через `frontend/src/pages/routes/GenerateRouteMobile.css`; декоративный фон результата на mobile отключён.

## Тесты

- `frontend/src/widgets/recommendation-route/RouteCandidateOptions.test.tsx`
- `frontend/src/widgets/recommendation-route/RouteWarnings.test.tsx`

## Что проверить на телефоне

- Вкладка `Маршрут` после построения не должна начинаться с огромной формы.
- Candidate options не должны показываться портянкой.
- Raw warning codes не должны быть видны пользователю.
- CTA должны быть доступны без длинного скролла.
