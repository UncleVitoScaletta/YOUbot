from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import sqlite3
import logging
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    description TEXT,
    budget TEXT,
    deadline TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    user_id INTEGER,
    message TEXT
)""")

conn.commit()

main_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add("📬 Мои задания")

@dp.message_handler(Text(equals="📬 Мои задания"))
async def my_tasks(message: types.Message):
    cursor.execute('SELECT id, title, description, budget, deadline FROM tasks WHERE user_id = ? ORDER BY id DESC LIMIT 5', (message.from_user.id,))
    tasks = cursor.fetchall()
    if not tasks:
        await message.answer("У вас пока нет размещённых заданий")
    else:
        for task in tasks:
            task_id, title, description, budget, deadline = task
            cursor.execute('SELECT user_id, message FROM responses WHERE task_id = ?', (task_id,))
            responses = cursor.fetchall()
            text = f"<b>{title}</b>\n{description}\n💸 Бюджет: {budget}\n⏳ Срок: {deadline}"
            if responses:
                text += f"\n\n<b>Отклики:</b>"
                for r_user_id, r_msg in responses:
                    text += f"\n— <i>Пользователь {r_user_id}:</i> {r_msg}"
            else:
                text += "\n\nНет откликов."
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{task_id}"),
                InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{task_id}")
            )
            await message.answer(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query_handler(lambda c: c.data.startswith("delete_"))
async def delete_task(callback_query: types.CallbackQuery):
    task_id = int(callback_query.data.split("_")[1])
    cursor.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, callback_query.from_user.id))
    cursor.execute('DELETE FROM responses WHERE task_id = ?', (task_id,))
    conn.commit()
    await bot.answer_callback_query(callback_query.id, text="Задание удалено.", show_alert=True)

class EditForm(StatesGroup):
    task_id = State()
    title = State()

@dp.callback_query_handler(lambda c: c.data.startswith("edit_"))
async def edit_task_start(callback_query: types.CallbackQuery, state: FSMContext):
    task_id = int(callback_query.data.split("_")[1])
    await state.update_data(task_id=task_id)
    await EditForm.title.set()
    await bot.send_message(callback_query.from_user.id, "Введите новый заголовок для задания:")

@dp.message_handler(state=EditForm.title)
async def edit_task_title(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute('UPDATE tasks SET title = ? WHERE id = ? AND user_id = ?', (message.text, data['task_id'], message.from_user.id))
    conn.commit()
    await message.answer("Заголовок обновлён!", reply_markup=main_kb)
    await state.finish()

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.answer("Добро пожаловать в YouDo Бот! Выберите действие:", reply_markup=main_kb)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
