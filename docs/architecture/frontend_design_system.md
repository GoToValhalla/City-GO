# City GO Frontend Design System

Документ фиксирует UI-фундамент для Web App и Telegram App. Дизайн-система развивается поэтапно: сначала токены и базовые компоненты, затем миграция пользовательских экранов мест и маршрутов.

## Design tokens

Основной файл: `frontend/src/styles/design-system.css`.

В нём определены:

- фоны: `--cg-bg-main`, `--cg-bg-card`, `--cg-bg-elevated`, `--cg-bg-muted`, `--cg-border-soft`;
- текст: `--cg-text-main`, `--cg-text-muted`, `--cg-text-soft`, `--cg-text-disabled`;
- акценты: `--cg-primary`, `--cg-primary-hover`, `--cg-primary-soft`, `--cg-route`, `--cg-open`, `--cg-warning`, `--cg-closed`, `--cg-rating`;
- радиусы: `--cg-radius-sm`, `--cg-radius-md`, `--cg-radius-lg`, `--cg-radius-xl`, `--cg-radius-pill`;
- тени: `--cg-shadow-card`, `--cg-shadow-sheet`, `--cg-shadow-primary`;
- типографика и utility-классы: `cg-text-h1`, `cg-text-h2`, `cg-text-card-title`, `cg-text-body`, `cg-text-caption`, `cg-text-button`, `cg-clamp-1`, `cg-clamp-2`, `cg-clamp-3`.

Подключение: `frontend/src/main.tsx`. Сначала подключаются `index.css` и `design-system.css`, затем `App.tsx` со стилями экранов. Это позволяет компонентным стилям уточнять токены без конфликтов порядка CSS.

## Базовые UI-компоненты

Компоненты лежат в `frontend/src/components/ui`.

| Компонент | Props / состояния | Ответственность |
|---|---|---|
| `Button` | `variant`, `size`, `loading`, `disabled`, `leftIcon`, `rightIcon` | Каноничная кнопка: `primary`, `secondary`, `ghost`, `danger`; размеры `sm`, `md`, `lg`. |
| `Card` | `variant` | Поверхность для мест, маршрутов и блоков деталей: `default`, `elevated`, `interactive`. |
| `StatusBadge` | `status: open/closed/unknown/soon` | Русские статусы: `Открыто`, `Закрыто`, `Уточнить`, `Скоро закроется`. |
| `RatingBadge` | `rating`, `reviewCount` | Рейтинг со звездой. При `null` ничего не рендерит. |
| `CategoryBadge` | `category` | Категория через русский `categoryLabel`, без сырых backend keys. |
| `DistanceBadge` | `distance` | Дистанция только если она есть. При `null` ничего не рендерит. |
| `Skeleton` | `variant` | Скелетон карточки/линии/круга, без белого экрана и текста `Загрузка`. |
| `EmptyState` | `title`, `description`, `actionLabel`, `onAction` | Пустое состояние с иконкой и опциональным CTA. Совместим со старым `message`. |
| `ErrorState` | `title`, `description`, `retryLabel`, `onRetry` | Ошибка на русском с кнопкой `Повторить`. |
| `PlacePhoto` | `imageUrl/photoUrl/photo_url`, `title/name`, `category`, `size`, `fallbackLabel`, `closed` | Фото места через `object-fit: cover`; при отсутствии/ошибке фото показывает тёмную заглушку с иконкой категории. Размеры `thumb`, `card`, `hero`. |

Экспорт: `frontend/src/components/ui/index.ts`.

## Place UI migration

Стили Place UI лежат в `frontend/src/styles/place-ui.css`.

Доменные компоненты мест лежат в `frontend/src/components/places`.

| Компонент / файл | Props / состояния | Ответственность |
|---|---|---|
| `placeViewModel.ts` | `Place`, `PlaceDetail` | Единые helpers для title, description, imageUrl, gallery, rating, reviewCount, distance, status, address, hours, tags/features. Скрывает `null`, `undefined`, `NaN` и сырые backend keys от UI. |
| `PlaceCard.tsx` | `place`, `active`, `className` | Кликабельная карточка места: фото 80/92 px, название до 2 строк, категория, статус, рейтинг только при наличии, дистанция только при наличии, описание только при наличии. Закрытое место получает красный бейдж и overlay на фото. |
| `PlaceList.tsx` | `places`, `loading`, `loadingMore`, `error`, `noCity`, `onRetry`, `onResetFilters`, `onSelectCity`, `activePlaceId` | Контейнер списка мест. Состояния: 5 skeleton-карточек при первой загрузке, 2 skeleton-карточки при дозагрузке, empty, error, no_city, success. При списке больше 50 включает CSS `content-visibility`. |
| `PlaceDetailSheet.tsx` | `place`, `onAddToRoute` | Детальная карточка места: hero-фото/заглушка, название, рейтинг/отзывы при наличии, категория, статус, описание с `Читать дальше`, блоки `Атмосфера`, `Что внутри`, `Кому подойдёт`, `Адрес`, `Часы работы`, `Контакты`, sticky footer с safe-area. Пустые блоки не рендерятся. |
| `SearchBar.tsx` / `CitySearchBar` | `value`, `onChange`, `placeholder`, `loading`, `error` | Поиск с debounce 300 ms, кнопкой очистки только при наличии текста, inline-ошибкой и loading внутри поля. |
| `FilterChips.tsx` | `options`, `value`, `onChange` | Горизонтальный скролл категорий, первый чип `Все`, активный чип на primary accent, disabled при `count=0`. |
| `FilterSheet.tsx` | `open`, `value`, `categories`, `supportsRadius`, `supportsRating`, `onApply`, `onReset`, `onClose` | Bottom sheet фильтров: категории, `Только открытые`, опционально радиус и рейтинг, кнопки `Применить` и `Сбросить`. |
| `PlaceMapPin.tsx` | `place`, `active`, `onClick` | Подготовленный пин карты: иконка категории, active-состояние, красный индикатор для закрытого места. |
| `PlaceMapBottomCard.tsx` | `place` | Нижняя карточка карты: фото/заглушка, название, категория, статус, переход в detail. |
| `index.ts` | exports | Единая точка импорта Place UI. |

## Переведённые экраны

| Экран / файл | Что изменено |
|---|---|
| `frontend/src/pages/places/PlacesListPage.tsx` | Переведён на `SearchBar`, `FilterChips`, `FilterSheet`, `PlaceList`; фильтры сбрасываются при смене города; loading/empty/error идут через новые компоненты. |
| `frontend/src/pages/places/PlaceDetailPage.tsx` | Убраны admin-verification действия и технические поля из пользовательского detail; экран теперь отвечает за загрузку/ошибку и рендерит `PlaceDetailSheet`. |
| `frontend/src/pages/open-now/OpenNowResults.tsx` | Результаты переведены на `PlaceList`, поэтому получают новые карточки и состояния. |
| `frontend/src/pages/nearby/NearbyResults.tsx` | Результаты переведены на `PlaceList`, дистанция отображается через `DistanceBadge`. |
| `frontend/src/features/places-list/usePlacesPagination.ts` | Добавлено состояние `error` и `retry`, чтобы ошибки загрузки не приводили к белым экранам. |
| `frontend/src/features/place-search/model/filterPlaces.ts` | Поиск стал устойчивым к пустым полям и ищет по русской категории. |
| `frontend/src/features/places-list/PlacesLoadMoreTrigger.tsx` | Sentinel стал невидимым, визуальная дозагрузка теперь через skeleton в `PlaceList`. |
| `frontend/src/entities/place/model/types.ts` | Добавлены optional frontend-поля для уже возможных данных API: `photo_url`, `image_urls`, `rating`, `review_count`, `phone`, `website`, `distance_*`, `working_hours`, `status` и др. Контракт API не менялся. |

## Обрабатываемые null/empty cases

- `photo/image_urls/photo_url`: `PlacePhoto` не рендерит `img`, если URL пустой, и переключается на fallback при `onError`.
- `rating/review_count`: `RatingBadge` не рендерится при `null`, `undefined` или нечисловом значении.
- `description`: блок не рендерится, если описания нет или оно совпадает с названием.
- `address`: detail не показывает блок адреса, если адрес не настоящий; список не выводит пустую строку.
- `working_hours/open_time/close_time`: блок часов не рендерится без данных.
- `phone/website`: CTA `Позвонить` и `Сайт` появляются только при наличии данных.
- `distance`: `DistanceBadge` появляется только при наличии расстояния.
- `category`: в UI используется русский `categoryLabel`.

## Что не менялось

- Backend не менялся.
- API endpoints и payload-контракты не менялись.
- Роутинг приложения не менялся.
- Карта мест не внедрялась в `/places`, потому что в текущей архитектуре этого экрана отдельной карты нет. Для будущей связки подготовлены `PlaceMapPin` и `PlaceMapBottomCard`.
- Полный редизайн home/routes/admin не выполнялся.

## Этап 3: Route UI Migration

Следующим этапом нужно привести маршруты к тому же канону:

1. `frontend/src/pages/routes/RouteDetailPage.tsx` и `frontend/src/widgets/route-navigation/*` — связать карту и список точек маршрута.
2. `RoutePointCard` — привести к карточке с фото, порядком посещения, статусом открытости и actions `Подробнее`, `Маршрут`, `Заменить`.
3. `RouteMapPreview` — привести пины к `PlaceMapPin`-подобному поведению: active, closed, selected.
4. `GenerateRoutePage` / result panel — убрать debug/admin-подачу из пользовательского первого экрана, оставить route summary, warnings и понятные CTA.
5. Проверить mobile/TMA safe-area для active route sticky controls.
