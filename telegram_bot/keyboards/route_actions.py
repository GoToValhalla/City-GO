from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_route_actions_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить точку"), KeyboardButton(text="Маршрут короче")],
            [KeyboardButton(text="Перестроить отсюда"), KeyboardButton(text="Убрать первую точку")],
            [KeyboardButton(text="📡 Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="🗺 Построить маршрут"), KeyboardButton(text="⚙️ Сменить город")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Например: добавить точку или маршрут длиннее",
    )
