# Playwright UI Tests

Локальная Playwright-среда живет в `ui-tests`.

## Первый запуск

```bash
cd /Users/user/City-GO/ui-tests
npm install
npm run install:browsers
npm run prepare:local
```

`prepare:local` пересоздает отдельную SQLite DB `ui_tests_local.db` из текущих
SQLAlchemy-моделей и добавляет минимальные публичные данные Зеленоградска для
smoke-проверок.

## Запуск

В первом терминале:

```bash
cd /Users/user/City-GO/ui-tests
npm run backend:local
```

Во втором терминале:

```bash
cd /Users/user/City-GO/ui-tests
npm run test:smoke:local
```

Полный UI-набор:

```bash
cd /Users/user/City-GO/ui-tests
npm run test:local
```

## Что важно

- `ui_tests_local.db` локальная и игнорируется Git.
- Команды используют тестовый локальный admin token, не production secret.
- Frontend dev server стартует из Playwright config на `127.0.0.1:5173`.
- Backend должен быть доступен на `127.0.0.1:8000`.
- В sandbox-среде запуск серверов может требовать elevated permission на bind localhost.
