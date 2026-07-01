from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_route_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить точку", callback_data="r:extend")],
            [InlineKeyboardButton(text="Маршрут короче", callback_data="r:shorter")],
            [InlineKeyboardButton(text="Перестроить отсюда", callback_data="r:rebuild")],
            [InlineKeyboardButton(text="Убрать первую точку", callback_data="r:drop_first")],
            [InlineKeyboardButton(text="🗺 Построить маршрут", callback_data="r:list:0")],
            [InlineKeyboardButton(text="⚙️ Сменить город", callback_data="c:list")],
        ],
    )
