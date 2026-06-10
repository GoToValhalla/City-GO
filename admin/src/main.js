import './style.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const sections = [
  ['dashboard', 'Дашборд'],
  ['cities', 'Города'],
  ['places', 'Места'],
  ['photos', 'Фото'],
  ['routes', 'Маршруты'],
  ['audit', 'Аудит'],
]

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`Ошибка API ${response.status}: ${text}`)
  }
  return response.json()
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]))
}

function renderLayout() {
  document.querySelector('#root').innerHTML = `
    <aside class="sidebar">
      <h1>Админка City Go</h1>
      <p>Управление городами, публикациями, карточками, фото, рейтингами, маршрутами и аудитом.</p>
      <nav>${sections.map(([id, title]) => `<button data-section="${id}">${title}</button>`).join('')}</nav>
    </aside>
    <main class="content"><div id="view"></div></main>
  `
  document.querySelectorAll('[data-section]').forEach((button) => {
    button.addEventListener('click', () => renderSection(button.dataset.section))
  })
}

async function renderSection(section) {
  const view = document.querySelector('#view')
  view.innerHTML = '<div class="card">Загрузка...</div>'
  try {
    if (section === 'dashboard') return renderDashboard()
    if (section === 'cities') return renderCities()
    if (section === 'places') return renderPlaces()
    if (section === 'photos') return renderPhotos()
    if (section === 'routes') return renderRoutes()
    if (section === 'audit') return renderAudit()
  } catch (error) {
    view.innerHTML = `<div class="card error">${escapeHtml(error.message)}</div>`
  }
}

async function renderDashboard() {
  const data = await api('/admin/dashboard')
  document.querySelector('#view').innerHTML = `
    <h2>Дашборд</h2>
    <div class="grid">
      ${metric('Городов всего', data.cities_total)}
      ${metric('Городов опубликовано', data.cities_published)}
      ${metric('Мест всего', data.places_total)}
      ${metric('Мест опубликовано', data.places_published)}
      ${metric('Мест скрыто', data.places_hidden)}
      ${metric('Мест на перепроверке', data.places_needs_recheck)}
      ${metric('Мест без фото', data.places_without_photo)}
      ${metric('Фото на проверке', data.pending_photos)}
      ${metric('Маршрутов всего', data.routes_total)}
      ${metric('Активных маршрутов', data.routes_active)}
      ${metric('Событий аудита', data.audit_events_total || 0)}
    </div>
  `
}

function metric(title, value) {
  return `<div class="card metric"><span>${escapeHtml(title)}</span><strong>${escapeHtml(value)}</strong></div>`
}

async function renderCities() {
  const [cities, jobs] = await Promise.all([api('/admin/cities?limit=50'), api('/admin/import-jobs?limit=50')])
  document.querySelector('#view').innerHTML = `
    <h2>Города</h2>
    <div class="card">
      <h3>Добавить город и запустить сбор данных</h3>
      <label>Название города</label>
      <input id="city-name" placeholder="Например, Калининград" />
      <label>Регион</label>
      <input id="city-region" placeholder="Например, Калининградская область" />
      <label>Страна</label>
      <input id="city-country" value="Россия" />
      <label>Радиус сбора, км</label>
      <input id="city-radius" type="number" value="15" min="1" max="200" />
      <button id="create-city">Создать город и собрать места/фото</button>
      <p id="city-result" class="muted"></p>
    </div>
    <h3>Список городов</h3>
    <table><thead><tr><th>Город</th><th>Статус</th><th>Места</th><th>Фото на проверке</th></tr></thead><tbody>
      ${cities.items.map((city) => `<tr><td>${escapeHtml(city.name)}<br><span class="muted">${escapeHtml(city.slug)}</span></td><td>${escapeHtml(city.launch_status)}</td><td>${city.places_published}/${city.places_total}</td><td>${city.pending_photos}</td></tr>`).join('')}
    </tbody></table>
    <h3>Задачи импорта</h3>
    <table><thead><tr><th>Город</th><th>Статус</th><th>Места</th><th>Следующий шаг</th></tr></thead><tbody>
      ${jobs.items.map((job) => `<tr><td>${escapeHtml(job.city_name)}</td><td>${escapeHtml(job.status)}</td><td>${job.places_total}</td><td>${escapeHtml(job.next_step)}</td></tr>`).join('')}
    </tbody></table>
  `
  document.querySelector('#create-city').addEventListener('click', async () => {
    const name = document.querySelector('#city-name').value.trim()
    const region = document.querySelector('#city-region').value.trim() || null
    const country = document.querySelector('#city-country').value.trim() || 'Россия'
    const radius = Number(document.querySelector('#city-radius').value || 15)
    const result = await api('/admin/cities/import', { method: 'POST', body: JSON.stringify({ name, region, country, radius_km: radius, actor: 'admin' }) })
    document.querySelector('#city-result').textContent = `${result.message} Slug: ${result.city_slug}`
  })
}

async function renderPlaces() {
  const data = await api('/admin/places?limit=50')
  document.querySelector('#view').innerHTML = `
    <h2>Места</h2>
    <div class="card">
      <h3>Ручное добавление места</h3>
      <div class="grid">
        <div><label>Название</label><input id="place-title" /></div>
        <div><label>Slug</label><input id="place-slug" /></div>
        <div><label>ID города</label><input id="place-city" type="number" value="1" /></div>
        <div><label>Категория</label><input id="place-category" placeholder="cafe, museum, park" /></div>
        <div><label>Широта</label><input id="place-lat" type="number" step="0.000001" /></div>
        <div><label>Долгота</label><input id="place-lng" type="number" step="0.000001" /></div>
      </div>
      <label>Описание</label><textarea id="place-description"></textarea>
      <button id="create-place">Добавить место как черновик</button>
      <p id="place-result" class="muted"></p>
    </div>
    <h3>Список мест</h3>
    <table><thead><tr><th>Название</th><th>Публикация</th><th>Достоверность</th><th>Фото</th><th>Действия</th></tr></thead><tbody>
      ${data.items.map((place) => `
        <tr>
          <td>${escapeHtml(place.title)}<br><span class="muted">${escapeHtml(place.slug)} · ${escapeHtml(place.category || '-')}</span></td>
          <td>${escapeHtml(place.publication_status)}<br>${place.is_published ? 'Показывается' : 'Скрыто'}</td>
          <td>${escapeHtml(place.existence_confidence_level)} / ${escapeHtml(place.existence_confidence_score)}</td>
          <td>${place.image_url ? 'Есть' : 'Нет'}</td>
          <td>
            <button data-publish="${place.id}">Опубликовать</button>
            <button data-unpublish="${place.id}">Снять</button>
            <button data-verify="${place.id}">Подтвердить</button>
          </td>
        </tr>`).join('')}
    </tbody></table>
  `
  document.querySelector('#create-place').addEventListener('click', async () => {
    const title = document.querySelector('#place-title').value.trim()
    const slug = document.querySelector('#place-slug').value.trim()
    const cityId = Number(document.querySelector('#place-city').value || 1)
    const category = document.querySelector('#place-category').value.trim() || null
    const lat = Number(document.querySelector('#place-lat').value)
    const lng = Number(document.querySelector('#place-lng').value)
    const short_description = document.querySelector('#place-description').value.trim() || null
    const result = await api('/admin/places?actor=admin', { method: 'POST', body: JSON.stringify({ title, slug, city_id: cityId, category, lat, lng, short_description, publication_status: 'draft' }) })
    document.querySelector('#place-result').textContent = `Место создано: ${result.title}`
  })
  bindPlaceActions()
}

function bindPlaceActions() {
  document.querySelectorAll('[data-publish]').forEach((button) => button.addEventListener('click', async () => {
    await api(`/admin/places/${button.dataset.publish}/publish`, { method: 'POST', body: JSON.stringify({ actor: 'admin', reason: 'Опубликовано из админки' }) })
    renderPlaces()
  }))
  document.querySelectorAll('[data-unpublish]').forEach((button) => button.addEventListener('click', async () => {
    await api(`/admin/places/${button.dataset.unpublish}/unpublish`, { method: 'POST', body: JSON.stringify({ actor: 'admin', reason: 'Снято с публикации из админки' }) })
    renderPlaces()
  }))
  document.querySelectorAll('[data-verify]').forEach((button) => button.addEventListener('click', async () => {
    await api(`/admin/places/${button.dataset.verify}/verify`, { method: 'POST', body: JSON.stringify({ actor: 'admin', reason: 'Место подтверждено' }) })
    renderPlaces()
  }))
}

async function renderPhotos() {
  const data = await api('/admin/place-images/pending?limit=50')
  document.querySelector('#view').innerHTML = `
    <h2>Фото</h2>
    <div class="card">
      <h3>Ручное добавление фото</h3>
      <label>ID места</label><input id="photo-place-id" type="number" />
      <label>URL фото</label><input id="photo-url" placeholder="https://..." />
      <label>Источник</label><input id="photo-source" value="manual_upload" />
      <label>Confidence 0..1</label><input id="photo-confidence" type="number" min="0" max="1" step="0.1" value="0.8" />
      <button id="create-photo">Добавить фото на проверку</button>
      <p id="photo-result" class="muted"></p>
    </div>
    <h3>Очередь проверки фото</h3>
    <table><thead><tr><th>Место</th><th>Фото</th><th>Источник</th><th>Confidence</th><th>Действия</th></tr></thead><tbody>
      ${data.items.map((item) => `<tr><td>${escapeHtml(item.place_title)}<br><span class="muted">${escapeHtml(item.place_slug)}</span></td><td><a href="${escapeHtml(item.image_url)}" target="_blank">Открыть фото</a></td><td>${escapeHtml(item.source_type)}</td><td>${escapeHtml(item.confidence ?? '-')}</td><td><button data-approve-photo="${item.image_id}">Подтвердить</button><button data-reject-photo="${item.image_id}">Отклонить</button></td></tr>`).join('')}
    </tbody></table>
  `
  document.querySelector('#create-photo').addEventListener('click', async () => {
    const place_id = Number(document.querySelector('#photo-place-id').value)
    const image_url = document.querySelector('#photo-url').value.trim()
    const source_type = document.querySelector('#photo-source').value.trim() || 'manual_upload'
    const confidence = Number(document.querySelector('#photo-confidence').value || 0.8)
    const result = await api('/admin/place-images', { method: 'POST', body: JSON.stringify({ place_id, image_url, source_type, confidence, actor: 'admin', comment: 'Ручное добавление из админки' }) })
    document.querySelector('#photo-result').textContent = `Фото добавлено в очередь: ${result.id}`
  })
  document.querySelectorAll('[data-approve-photo]').forEach((button) => button.addEventListener('click', async () => {
    await api(`/admin/place-images/${button.dataset.approvePhoto}/approve`, { method: 'POST', body: JSON.stringify({ reviewer: 'admin', comment: 'Фото подтверждено' }) })
    renderPhotos()
  }))
  document.querySelectorAll('[data-reject-photo]').forEach((button) => button.addEventListener('click', async () => {
    await api(`/admin/place-images/${button.dataset.rejectPhoto}/reject`, { method: 'POST', body: JSON.stringify({ reviewer: 'admin', comment: 'Фото отклонено' }) })
    renderPhotos()
  }))
}

async function renderRoutes() {
  const data = await api('/admin/routes?limit=50')
  document.querySelector('#view').innerHTML = `
    <h2>Маршруты</h2>
    <div class="card">
      <h3>Создать editorial route</h3>
      <div class="grid"><div><label>ID города</label><input id="route-city" type="number" value="1" /></div><div><label>Slug</label><input id="route-slug" /></div><div><label>Название</label><input id="route-title" /></div><div><label>Режим</label><input id="route-mode" value="walk" /></div></div>
      <label>Описание</label><textarea id="route-description"></textarea>
      <button id="create-route">Создать маршрут</button>
      <p id="route-result" class="muted"></p>
    </div>
    <table><thead><tr><th>Название</th><th>Активен</th><th>Длительность</th><th>Действия</th></tr></thead><tbody>
      ${data.items.map((route) => `<tr><td>${escapeHtml(route.title)}<br><span class="muted">${escapeHtml(route.slug)}</span></td><td>${route.is_active ? 'Да' : 'Нет'}</td><td>${route.duration_minutes || '-'} мин</td><td><button data-route-publish="${route.id}">Опубликовать</button><button data-route-unpublish="${route.id}">Снять</button></td></tr>`).join('')}
    </tbody></table>
  `
  document.querySelector('#create-route').addEventListener('click', async () => {
    const city_id = Number(document.querySelector('#route-city').value || 1)
    const slug = document.querySelector('#route-slug').value.trim()
    const title = document.querySelector('#route-title').value.trim()
    const route_mode = document.querySelector('#route-mode').value.trim() || 'walk'
    const short_description = document.querySelector('#route-description').value.trim() || null
    const result = await api('/admin/routes', { method: 'POST', body: JSON.stringify({ city_id, slug, title, route_mode, short_description, actor: 'admin' }) })
    document.querySelector('#route-result').textContent = `Маршрут создан: ${result.title}`
  })
  document.querySelectorAll('[data-route-publish]').forEach((button) => button.addEventListener('click', async () => {
    await api(`/admin/routes/${button.dataset.routePublish}/publish`, { method: 'POST', body: JSON.stringify({ actor: 'admin' }) })
    renderRoutes()
  }))
  document.querySelectorAll('[data-route-unpublish]').forEach((button) => button.addEventListener('click', async () => {
    await api(`/admin/routes/${button.dataset.routeUnpublish}/unpublish`, { method: 'POST', body: JSON.stringify({ actor: 'admin', reason: 'Снято из админки' }) })
    renderRoutes()
  }))
}

async function renderAudit() {
  const data = await api('/admin/audit-log?limit=50')
  document.querySelector('#view').innerHTML = `
    <h2>Аудит</h2>
    <table><thead><tr><th>Дата</th><th>Кто</th><th>Действие</th><th>Сущность</th><th>Причина</th></tr></thead><tbody>
      ${data.items.map((item) => `<tr><td>${escapeHtml(item.created_at)}</td><td>${escapeHtml(item.actor)}</td><td>${escapeHtml(item.action)}</td><td>${escapeHtml(item.entity_type)} ${escapeHtml(item.entity_id || '')}</td><td>${escapeHtml(item.reason || '-')}</td></tr>`).join('')}
    </tbody></table>
  `
}

renderLayout()
renderSection('dashboard')
