from aiogram import types, Router, F
from aiogram.filters import CommandStart, Command, or_f
from tg_bot.keyboards import reply

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter