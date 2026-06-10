# City Go — добавление и обновление города для DevOps

Дата создания: 2026-06-06.

## 1. Главный принцип

Новый город нельзя публиковать автоматически. Правильный порядок:

создать город → собрать места → собрать фото → нормализовать данные → проверить coverage → провести модерацию → опубликовать.

## 2. Добавление города через админку

Admin frontend вызывает `POST /admin/cities/import`.

Backend должен:

1. Нормализовать название города.
2. Сгенерировать slug.
3. Создать запись в `cities`.
4. Поставить `launch_status = importing`.
5. Поставить `is_active = false`.
6. Записать audit log с действием `create_city_import_request`.
7. Вернуть `job_status = queued`.

После этого отдельный worker или production script должен собрать места и фото.

## 3. Что делает import worker

Для города нужно выполнить:

1. Geocoding города, если координаты центра не заданы.
2. OSM/Overpass сбор мест.
3. Нормализацию категорий.
4. Удаление дублей.
5. Отсев технического мусора.
6. Создание import batch.
7. Создание мест как draft/unpublished.
8. Сбор фото-кандидатов.
9. Создание `place_images` со статусом `needs_review`.
10. Перевод города в `launch_status = review_required`.

Новые места после импорта должны быть скрыты из публичного продукта до проверки.

## 4. Проверка перед публикацией города

Перед публикацией проверить `GET /place-coverage/{city_slug}`.

Минимально проверить:

- всего мест;
- координаты;
- категории;
- фото;
- opening hours;
- verified places;
- published places;
- кофе;
- еда;
- прогулки;
- культура;
- dog-friendly;
- family-friendly;
- indoor/outdoor.

## 5. Модерация после импорта

Админ должен:

1. Открыть `/admin/places`.
2. Проверить draft/unverified места.
3. Исправить карточки.
4. Подтвердить место через `POST /admin/places/{place_id}/verify`.
5. Проверить фото через `/admin/place-images/pending`.
6. Подтвердить или отклонить фото.
7. Опубликовать место через `POST /admin/places/{place_id}/publish`.

## 6. Публикация города

Город можно публиковать, когда:

- достаточно мест;
- ключевые категории покрыты;
- нет критичных дублей;
- мусорные категории скрыты;
- есть verified places;
- фото не выдают area/category fallback за exact place photo;
- route builder строит маршрут без пустого результата.

После проверки город переводится в `launch_status = published` и `is_active = true`.

## 7. Обновление города

Обновление города должно идти через dry-run-first процесс:

refresh snapshot → dry-run import → diff review → real import → coverage check → moderation queue.

Запрещено:

- удалять production places напрямую;
- автоматически публиковать новые места;
- автоматически заменять подтверждённое фото непроверенным;
- автоматически скрывать место без audit reason.

## 8. Пропавшие места

Если место пропало из источника:

1. Не удалять.
2. Пометить как needs recheck.
3. Создать verification task.
4. Скрывать только после подтверждения проблемы.

## 9. Rollback

Для полноценного production flow нужен rollback import batch. До его реализации:

- делать backup БД перед real import;
- запускать real import только после dry-run;
- писать audit log;
- опасные операции делать вручную.

## 10. DevOps checklist

1. Проверить миграции.
2. Сделать backup БД.
3. Создать город через `/admin/cities/import`.
4. Запустить import worker или production import script.
5. Проверить import logs.
6. Проверить coverage endpoint.
7. Проверить очередь фото.
8. Проверить draft/unverified places.
9. Опубликовать только проверенные места.
10. Проверить публичный каталог.
11. Проверить open-now.
12. Проверить nearby.
13. Проверить route build.
14. После smoke перевести город в published.
