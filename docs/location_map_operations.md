# Геолокация и карта: эксплуатация

## Переменные окружения

- `VITE_MAP_STYLE_URL` — URL MapLibre style JSON. Если пусто, используется raster style.
- `VITE_MAP_TILE_URL` — шаблон raster tiles для development fallback.
- `VITE_MAP_ATTRIBUTION` — обязательная атрибуция tile provider.
- `VITE_LOCATION_TTL_SECONDS` — TTL временной позиции, по умолчанию 900 секунд.

Ключи tile provider не коммитятся. Если style или tiles недоступны, список мест
остаётся рабочим, а карта показывает русское сообщение об ошибке.

## HTTPS

Browser Geolocation работает только на HTTPS и localhost. На HTTP/IP приложение
не вызывает API браузера и предлагает ручную точку или центр города. Telegram
Mini App может использовать native `LocationManager` независимо от browser
provider, но сама Mini App должна быть опубликована по HTTPS.

## BotFather и Mini App

1. Указать production HTTPS URL как Main Mini App.
2. Убедиться, что клиент Telegram поддерживает Bot API 8.0+.
3. Проверить Location Services устройства и доступ Telegram к геопозиции.
4. Reply-кнопка `Отправить геопозицию` должна иметь `request_location=True`.

## Privacy и TTL

Frontend хранит точную позицию в памяти/session storage не дольше TTL. Bot
сохраняет позицию с `expires_at`, удаляет её после Nearby и игнорирует
просроченные значения. Координаты не передаются в analytics и не входят в
обычный request log. Допустимы provider, outcome, scenario и coarse accuracy.

## Fallback-сценарии

| Состояние | Действия |
|---|---|
| Telegram denied | Открыть настройки Telegram, ручная точка, центр города |
| Telegram API отсутствует | Browser Geolocation |
| Browser denied/timeout | Повторить, ручная точка, центр города |
| HTTP/IP | Ручная точка, центр города, Telegram native |
| WebGL/style/tile error | Список мест и outbound-карты |
| Bot intent истёк | Понятное меню и новый запрос геопозиции |

## Проверка платформ

- iOS Telegram: native location, settings, safe area, bottom sheet.
- Android Telegram: native location, haptic feedback, viewport resize.
- Telegram Desktop: browser fallback или ручная точка.
- Web: HTTPS grant/deny/timeout и watcher cleanup.
- Viewports: 360, 390, 768, 1024 и 1440 px.

## Troubleshooting

- Чёрный canvas: проверить WebGL, style URL, CORS tiles и attribution.
- Карта пустая: проверить координаты и network requests; список не должен исчезать.
- GPS не обновляется: watcher работает только при активном маршруте.
- Telegram settings не открываются: вызывать кнопку только после `LocationManager.init`.
