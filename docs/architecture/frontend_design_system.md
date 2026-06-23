# City GO Frontend Design System

Документ фиксирует базовый UI-фундамент для Web App и Telegram App. На этапе 1 дизайн-система добавлена как слой поверх текущего фронтенда: бизнес-логика, API-контракты и роутинг не менялись.

## Где лежат design tokens

Основной файл: `frontend/src/styles/design-system.css`.

В нём определены:

- фоны: `--cg-bg-main`, `--cg-bg-card`, `--cg-bg-elevated`, `--cg-bg-muted`, `--cg-border-soft`;
- текст: `--cg-text-main`, `--cg-text-muted`, `--cg-text-soft`, `--cg-text-disabled`;
- акценты: `--cg-primary`, `--cg-primary-hover`, `--cg-primary-soft`, `--cg-route`, `--cg-open`, `--cg-warning`, `--cg-closed`, `--cg-rating`;
- радиусы: `--cg-radius-sm`, `--cg-radius-md`, `--cg-radius-lg`, `--cg-radius-xl`, `--cg-radius-pill`;
- тени: `--cg-shadow-card`, `--cg-shadow-sheet`, `--cg-shadow-primary`;
- типографика и utility-классы: `cg-text-h1`, `cg-text-h2`, `cg-text-card-title`, `cg-text-body`, `cg-text-caption`, `cg-text-button`, `cg-clamp-1`, `cg-clamp-2`, `cg-clamp-3`.

Файл подключён в `frontend/src/main.tsx` после текущих стилей, чтобы новый слой мог задавать глобальные токены и постепенно принимать старые экраны на себя.

## Базовые UI-компоненты

Компоненты лежат в `frontend/src/components/ui`.

| Компонент | Ответственность |
|---|---|
| `Button` | Каноничная кнопка: `primary`, `secondary`, `ghost`, `danger`; размеры `sm`, `md`, `lg`; состояния disabled/loading. |
| `Card` | Базовая поверхность для мест, маршрутов и блоков деталей: `default`, `elevated`, `interactive`. |
| `StatusBadge` | Русские статусы мест: `Открыто`, `Закрыто`, `Уточнить`, `Скоро закроется`. |
| `RatingBadge` | Рейтинг со звездой. Если рейтинга нет, компонент ничего не рендерит. |
| `CategoryBadge` | Категория места через русский `categoryLabel`, без сырых backend keys. |
| `Skeleton` | Скелетон в форме карточки, без белого экрана и текстовой заглушки загрузки. |
| `EmptyState` | Пустое состояние: иконка, заголовок, описание, опциональный CTA. Сохранена совместимость со старым `message`. |
| `ErrorState` | Ошибка на русском с кнопкой `Повторить`. |
| `PlacePhoto` | Фото места с `object-fit: cover`; при отсутствии/ошибке фото показывает тёмную заглушку с иконкой категории; размеры `thumb`, `card`, `hero`. |

Для удобного импорта добавлен `frontend/src/components/ui/index.ts`.

## Что не менялось на этапе 1

- Backend и API-контракты не менялись.
- Роутинг приложения не менялся.
- Полный редизайн страниц не выполнялся.
- Табличный/admin-подход не переносился в пользовательский UI.
- Существующие страницы пока не переписаны на новые компоненты, кроме подключения глобального слоя токенов.

## Следующий этап: Place UI migration

Следующим этапом нужно мигрировать пользовательские экраны мест и маршрутов на новые компоненты.

Приоритет миграции:

1. `frontend/src/components/places/PlaceCard.tsx` — заменить локальную разметку фото/категории на `PlacePhoto`, `CategoryBadge`, `StatusBadge`, `RatingBadge`, `Button/Card`.
2. `frontend/src/pages/places/PlacesListPage.tsx` — заменить текстовые loading/empty-состояния на `Skeleton`, `EmptyState`, `ErrorState`.
3. `frontend/src/pages/places/PlaceDetailPage.tsx` — заменить hero-фото на `PlacePhoto`, действия на `Button`, факты на badges, убрать технические/admin-данные из пользовательского первого экрана.
4. `frontend/src/pages/routes/RouteDetailPage.tsx` и `frontend/src/widgets/route-navigation/*` — привести маршрут к канону `карта + список`, порядок посещения, понятные действия `Подробнее`, `Маршрут`, `Заменить`, `Позвонить`, `Сайт`.
5. `frontend/src/widgets/home/*` — убрать старую светлую подачу и собрать главный экран из каноничных карточек, кнопок и состояний.

Для каждой миграции сначала менять один экран, запускать frontend lint/build/test, затем переходить к следующему экрану.
