from aiogram.fsm.state import StatesGroup, State

class Keywords(StatesGroup):
    waiting_for_keywords = State()