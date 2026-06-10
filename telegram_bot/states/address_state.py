"""
FSM-состояния для ручного ввода адреса в Telegram-боте City GO.
"""

from aiogram.fsm.state import State, StatesGroup


class AddressInputState(StatesGroup):
    """
    Состояния сценария ручного ввода адреса.
    """

    waiting_for_address = State()