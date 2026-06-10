# ADMIN_API_TOKEN — ручная настройка (сервер + GitHub + frontend build)

> Cursor не имеет SSH-доступа к production. Выполняйте шаги ниже вручную.
> **Не коммитьте и не вставляйте реальный токен в git, чаты и скриншоты.**

---

## 0. Одна цель

Один и тот же секретный токен должен попасть в **три места**:

| # | Где | Переменная |
|---|-----|------------|
| 1 | Сервер `/srv/app/.env` | `ADMIN_API_TOKEN` |
| 2 | GitHub Actions Secret | `ADMIN_API_TOKEN` |
| 3 | Сборка frontend (Docker build-arg / локально `.env.local`) | `VITE_ADMIN_API_TOKEN` |

Backend и frontend **обязаны совпадать**, иначе публичный API может жить, а `/admin` получит 401.

---

## 1. Сгенерировать токен (локально, один раз)

На своём компьютере:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Скопируйте вывод в буфер обмена. Дальше везде подставляйте **это значение** (в командах ниже — `<YOUR_TOKEN>`).

---

## 2. Сервер: `/srv/app/.env` + перезапуск backend

### 2.1 Подключение

```bash
ssh -p <SSH_PORT> <SSH_USER>@<SERVER_HOST>
cd /srv/app
```

`<SSH_PORT>`, `<SSH_USER>`, `<SERVER_HOST>` — из ваших GitHub Secrets (`SSH_PORT`, `SSH_USER`, `SSH_HOST`).

### 2.2 Резервная копия `.env`

```bash
cp .env .env.bak.$(date +%Y%m%d_%H%M%S)
```

### 2.3 Проверить, есть ли уже токен

```bash
grep -n '^ADMIN_API_TOKEN=' .env || echo "ADMIN_API_TOKEN: not set"
grep -n '^APP_ENV=' .env || echo "APP_ENV: not set"
```

### 2.4 Добавить или обновить токен

**Если строки `ADMIN_API_TOKEN=` нет:**

```bash
printf '%s\n' 'ADMIN_API_TOKEN=<YOUR_TOKEN>' >> .env
```

**Если строка уже есть — заменить (без дубликата):**

```bash
sed -i.bak '/^ADMIN_API_TOKEN=/d' .env
printf '%s\n' 'ADMIN_API_TOKEN=<YOUR_TOKEN>' >> .env
```

**Убедиться, что production-режим включён (если строки нет):**

```bash
grep -q '^APP_ENV=' .env || printf '%s\n' 'APP_ENV=production' >> .env
```

### 2.5 Перезапустить backend (и frontend при необходимости)

```bash
docker compose up -d backend frontend
```

### 2.6 Проверки на сервере

```bash
# Статус контейнеров
docker compose ps

# Логи backend — не должно быть RuntimeError про ADMIN_API_TOKEN
docker compose logs --tail=50 backend

# Health внутри контейнера
docker compose exec -T backend curl -sf http://localhost:8000/health

# Readiness (если endpoint есть)
docker compose exec -T backend curl -sf http://localhost:8000/ready || true

# Публичные места (пример: kaliningrad)
docker compose exec -T backend curl -sf 'http://localhost:8000/places?city_slug=kaliningrad&limit=3' | head -c 500
echo
```

### 2.7 Проверки снаружи (с вашего компьютера)

```bash
curl -sf http://<SERVER_HOST>/api/health
curl -sf 'http://<SERVER_HOST>/api/places?city_slug=kaliningrad&limit=3' | head -c 500
echo
```

Ожидание: JSON, не HTML с `502 Bad Gateway`.

---

## 3. GitHub Secret: `ADMIN_API_TOKEN`

### 3.1 Через веб-интерфейс

1. Откройте: `https://github.com/GoToValhalla/app/settings/secrets/actions`
2. **New repository secret**
3. **Name:** `ADMIN_API_TOKEN` (имя точное, регистр важен)
4. **Secret:** вставьте `<YOUR_TOKEN>` (тот же, что в `/srv/app/.env`)
5. **Add secret**

### 3.2 Через GitHub CLI (опционально)

```bash
gh secret set ADMIN_API_TOKEN --repo GoToValhalla/app --body '<YOUR_TOKEN>'
```

Проверка (имя есть, значение не показывается):

```bash
gh secret list --repo GoToValhalla/app | grep ADMIN_API_TOKEN
```

### 3.3 Зачем secret

- Deploy дописывает `ADMIN_API_TOKEN` в `/srv/app/.env`, если на сервере ещё нет строки.
- Сборка frontend в CI/CD получает `VITE_ADMIN_API_TOKEN` из того же secret (build-arg).

После добавления secret: **Actions → Build & Deploy → Run workflow** (или push в `master`).

---

## 4. Frontend: токен из build variable (не из кода)

Исходники читают `import.meta.env.VITE_ADMIN_API_TOKEN` (`frontend/src/pages/admin/adminToken.ts`).

### 4.1 Локальная разработка

```bash
cd frontend
cp .env.example .env.local
# В .env.local задайте VITE_ADMIN_API_TOKEN=<YOUR_TOKEN> (тот же, что на backend)
npm run dev
```

`.env.local` в git не коммитить.

### 4.2 Production Docker / GitHub Actions

`frontend/Dockerfile` принимает build-arg `VITE_ADMIN_API_TOKEN`.
Workflow `deploy.yml` передаёт `${{ secrets.ADMIN_API_TOKEN }}` при сборке образа.

После push с этими изменениями и заданного secret frontend пересоберётся автоматически.

---

## 5. Чеклист «всё готово»

- [ ] `curl http://<SERVER_HOST>/api/health` → OK
- [ ] `curl 'http://<SERVER_HOST>/api/places?city_slug=kaliningrad&limit=1'` → не пустой JSON / не 502
- [ ] `docker compose logs backend` — нет `ADMIN_API_TOKEN must be set`
- [ ] GitHub Secret `ADMIN_API_TOKEN` создан
- [ ] `/admin` после логина открывает dashboard без 401 на API
- [ ] Реальный токен **не** в git, не в issue/PR, не в логах CI

---

## 6. Частые ошибки

| Симптом | Причина | Что сделать |
|---------|---------|-------------|
| 502 на `/api/*` | backend crash-loop | Проверить `.env`, перезапустить backend |
| Места пустые, frontend открывается | API мёртв, не БД | Сначала `/api/health` |
| Admin 401 | токен frontend ≠ backend | Выровнять `VITE_*` и `ADMIN_API_TOKEN` |
| Две строки `ADMIN_API_TOKEN` в `.env` | ручное дублирование | Оставить одну через `sed` выше |
| Deploy success, API мёртв | health gate / старый образ | Логи `docker compose logs backend` на сервере |

---

## Связанные файлы

- Backend fail-fast: `main.py`
- Deploy inject: `.github/workflows/deploy.yml`
- Frontend token: `frontend/src/pages/admin/adminToken.ts`
- Пример env: `frontend/.env.example`, корневой `.env.example`
