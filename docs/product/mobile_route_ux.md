# CITYGO-161 · Mobile Route UX

## Реализовано

- Форма построения маршрута после успешной сборки сворачивается в compact details на странице `frontend/src/pages/routes/GenerateRoutePage.tsx`.
- Первый экран результата теперь показывает главное: статус, количество мест, время, расстояние, качество и основные CTA.
- Основные CTA находятся в `RouteResultPanel`: `Пересобрать`, `Добавить место`, `Заменить точку`, `Начать маршрут`.
- Active route session controls в `RouteResultPanel` используют backend session API, а не только локальное состояние.
- Первое доступное фото маршрута выводится в compact insights через `RouteInsights`, чтобы результат не выглядел пустым при наличии `image_url` у точек.
- Предупреждения маршрута свернуты в блок `Есть нюансы данных` без raw technical codes: `frontend/src/widgets/recommendation-route/RouteWarnings.tsx`.
- Доступные candidate options спрятаны под accordion `Добавить место` и ограничены шестью карточками: `RouteCandidateOptions.tsx`.
- Карточки точек маршрута сокращены до названия, категории, адреса, времени визита, критичного предупреждения и действий: `RoutePointList.tsx`.
- Уменьшена визуальная нагрузка мобильного результата через `frontend/src/pages/routes/GenerateRouteMobile.css`; декоративный фон результата на mobile отключён.

## Тесты

- `frontend/src/widgets/recommendation-route/RouteCandidateOptions.test.tsx`
- `frontend/src/widgets/recommendation-route/RouteWarnings.test.tsx`
- `frontend/src/widgets/recommendation-route/RoutePointList_missing_address_new.test.tsx`
- `frontend/src/widgets/recommendation-route/RouteResultPanel.test.tsx` сейчас smoke-only после стабилизации compact UI; полноценные assertions по CTA/active session нужно восстановить отдельным frontend-test hardening pass.

## Что проверить на телефоне

- Вкладка `Маршрут` после построения не должна начинаться с огромной формы.
- Candidate options не должны показываться портянкой.
- Raw warning codes не должны быть видны пользователю.
- CTA должны быть доступны без длинного скролла.
- Если у первой/любой точки есть фото, compact result должен показывать route photo в блоке результата.
- `Начать маршрут`, `Я на месте`, `Пропустить`, `Пауза`, `Завершить` должны работать через backend session и сохранять состояние между перерендерами.
