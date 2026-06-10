OPEN_NOW_EMPTY_TEMPLATE = (
    "Сейчас не нашел открытых мест для города:\n"
    "<b>{city_slug}</b>"
)

NEARBY_EMPTY_TEMPLATE = (
    "Рядом ничего не найдено.\n\n"
    "Координаты:\n"
    "lat: <b>{lat}</b>\n"
    "lng: <b>{lng}</b>\n"
    "radius_km: <b>{radius_km}</b>"
)

COFFEE_EMPTY_TEMPLATE = (
    "Не нашел места с кофе по текущим фильтрам.\n\n"
    "Город: <b>{city_slug}</b>"
)

FOOD_EMPTY_TEMPLATE = (
    "Не нашел места, где поесть, по текущим фильтрам.\n\n"
    "Город: <b>{city_slug}</b>"
)

WALKS_EMPTY_TEMPLATE = (
    "Не нашел места для прогулки по текущим фильтрам.\n\n"
    "Город: <b>{city_slug}</b>"
)

DOG_FRIENDLY_EMPTY_TEMPLATE = (
    "Не нашел dog-friendly места по текущим фильтрам.\n\n"
    "Город: <b>{city_slug}</b>"
)

OPEN_NOW_RESULT_HEADER_TEMPLATE = (
    "<b>Открыто сейчас</b>\n"
    "Город: <b>{city_slug}</b>\n\n"
)

NEARBY_RESULT_HEADER_TEMPLATE = (
    "<b>Места рядом</b>\n"
    "lat: <b>{lat}</b>\n"
    "lng: <b>{lng}</b>\n"
    "radius_km: <b>{radius_km}</b>\n\n"
)

COFFEE_RESULT_HEADER_TEMPLATE = (
    "<b>Где кофе</b>\n"
    "Город: <b>{city_slug}</b>\n\n"
)

FOOD_RESULT_HEADER_TEMPLATE = (
    "<b>Где поесть</b>\n"
    "Город: <b>{city_slug}</b>\n\n"
)

WALKS_RESULT_HEADER_TEMPLATE = (
    "<b>Куда погулять</b>\n"
    "Город: <b>{city_slug}</b>\n\n"
)

DOG_FRIENDLY_RESULT_HEADER_TEMPLATE = (
    "<b>С собакой</b>\n"
    "Город: <b>{city_slug}</b>\n\n"
)

RESULT_ITEM_TEMPLATE = "• <b>{title}</b>"

PLACE_CARD_PHOTO_UNAVAILABLE = "Фото: недоступно"
