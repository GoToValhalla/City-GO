# Откат taxonomy batch

1. Открыть `/admin/taxonomy?tab=bulk` и найти batch ID в аудите.
2. Убедиться, что batch имеет статус `applied`.
3. Проверить примеры и количество изменений.
4. Вызвать `POST /admin/taxonomy/bulk/{batch_id}/rollback` или кнопку «Откатить».
5. Проверить `rollback_result.restored` и пропущенные записи.
6. Пропущенная запись означает, что её категория была изменена после batch; автоматический rollback намеренно не затирает это изменение.
7. Проверить workflow `after_category_change` для восстановленных мест и route cache.

Rollback идемпотентен. Повторный вызов возвращает тот же завершённый batch.
