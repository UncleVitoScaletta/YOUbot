
class ChatForm(StatesGroup):
    partner_id = State()
    waiting_message = State()


from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
import sqlite3

BOT_TOKEN = "ВАШ_ТОКЕН_СЮДА"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- Клавиатура ---
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(
    KeyboardButton("📝 Создать задание"),
    KeyboardButton("📬 Мои задания")
)
main_kb.add(
    KeyboardButton("🔍 Найти задания"),
    KeyboardButton("⚙️ Настройки")
)

# --- База данных ---
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    description TEXT,
    budget TEXT,
    deadline TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER,
    user_id INTEGER,
    message TEXT
)
""")
conn.commit()

# --- FSM для отклика ---
class ResponseForm(StatesGroup):
    task_id = State()
    message = State()

# --- Команды ---
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.answer("Привет! Я помогу тебе найти исполнителей или задания 🔧", reply_markup=main_kb)

@dp.message_handler(Text(equals="📝 Создать задание"))
async def create_task(message: types.Message):
    await message.answer("Форма создания задания в разработке. Скоро будет доступна!")

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
            cursor.execute("SELECT executor_id, status FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row and row[0]:
                text += f"\n🧑‍🔧 Исполнитель: {row[0]}"
                kb.add(InlineKeyboardButton("👤 Профиль исполнителя", callback_data=f"profile_{row[0]}"))
                text += f"\n📌 Статус: {row[1]}"
            if responses:
                text += f"\n\n<b>Отклики:</b>"
                for r_user_id, r_msg in responses:
                    text += f"\n— <i>Пользователь {r_user_id}:</i> {r_msg}"
            kb.add(InlineKeyboardButton("✅ Назначить исполнителем", callback_data=f"assign_{task_id}_{r_user_id}"))
            kb.add(InlineKeyboardButton("💬 Написать", callback_data=f"chat_{r_user_id}"))
            else:
                text += "\n\nНет откликов."
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("✅ Завершить задание", callback_data=f"complete_{task_id}"),
                InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{task_id}"),
                InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{task_id}"), InlineKeyboardButton("✅ Завершить", callback_data=f"finish_{task_id}")
            )
            await message.answer(text, reply_markup=kb, parse_mode='HTML')

@dp.message_handler(Text(equals="🔍 Найти задания"))
async def find_tasks(message: types.Message):
    cursor.execute('SELECT id, title, description, budget FROM tasks ORDER BY id DESC LIMIT 5')
    tasks = cursor.fetchall()
    if not tasks:
        await message.answer("Заданий пока нет.")
    else:
        for task_id, title, description, budget in tasks:
            text = f"<b>{title}</b>\n{description}\n💸 Бюджет: {budget}"
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton("✉️ Откликнуться", callback_data=f"respond_{task_id}")
            )
            await message.answer(text, reply_markup=kb, parse_mode='HTML')

@dp.message_handler(Text(equals="⚙️ Настройки"))
async def settings(message: types.Message):
    await message.answer("Здесь будут настройки профиля.")

@dp.callback_query_handler(lambda c: c.data.startswith("respond_"))
async def respond_to_task(callback_query: types.CallbackQuery, state: FSMContext):
    task_id = int(callback_query.data.split("_")[1])
    await state.update_data(task_id=task_id)
    await ResponseForm.message.set()
    await bot.send_message(callback_query.from_user.id, "Введите ваше сообщение для отклика:")

@dp.message_handler(state=ResponseForm.message)
async def process_response(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO responses (task_id, user_id, message) VALUES (?, ?, ?)",
                   (data["task_id"], message.from_user.id, message.text))
    conn.commit()
    await message.answer("Ваш отклик отправлен!", reply_markup=main_kb)
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)



class TaskForm(StatesGroup):
    rate = State()
    title = State()
    category = State()
    description = State()
    budget = State()
    deadline = State()

@dp.message_handler(Text(equals="📝 Создать задание"))
async def create_task(message: types.Message):
    await message.answer("Введите заголовок задания:")
    await TaskForm.title.set()

# СТАРЫЙ ХЭНДЛЕР УДАЛЁН(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание задания:")
    await TaskForm.description.set()

@dp.message_handler(state=TaskForm.description)
async def task_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Укажите бюджет (например, 1000 руб):")
    await TaskForm.budget.set()

@dp.message_handler(state=TaskForm.budget)
async def task_budget(message: types.Message, state: FSMContext):
    await state.update_data(budget=message.text)
    await message.answer("Укажите срок выполнения (например, 2 дня):")
    await TaskForm.deadline.set()

@dp.message_handler(state=TaskForm.deadline)
async def task_deadline(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO tasks (user_id, title, description, budget, deadline) VALUES (?, ?, ?, ?, ?)",
                   (message.from_user.id, data["title"], data["description"], data["budget"], message.text))
    conn.commit()
    await message.answer("✅ Задание создано и добавлено в базу данных!", reply_markup=main_kb)
    await state.finish()



@dp.message_handler(state=TaskForm.title)
async def task_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)

    kb = InlineKeyboardMarkup(row_width=2)
    categories = [
        "Курьерские услуги", "Уборка", "Грузоперевозки", "Ремонт и строительство",
        "Ремонт цифровой техники", "Компьютерная помощь", "Дизайн", "Разработка ПО",
        "Фото и видео", "Мероприятия и промоакции", "Репетиторы и обучение", "Юридическая помощь",
        "Красота и здоровье", "Виртуальный помощник", "Домашний персонал", "Установка техники",
        "Ремонт авто", "Выездная автоуслуга", "Фриланс", "Другое"
    ]
    for name in categories:
        kb.insert(InlineKeyboardButton(name, callback_data=f"cat_{name}"))

    await message.answer("Выберите категорию задания:", reply_markup=kb)
    await TaskForm.category.set()

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"), state=TaskForm.category)
async def select_category(callback_query: types.CallbackQuery, state: FSMContext):
    category = callback_query.data[4:]
    await state.update_data(category=category)
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Введите описание задания:")
    await TaskForm.description.set()



@dp.message_handler(Text(equals="👤 Профиль"))
async def user_profile(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.full_name

    # Получаем статистику
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,))
    posted = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE performer_id = ?", (user_id,))
    completed = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(rating) FROM ratings WHERE user_id = ?", (user_id,))
    avg_rating = cursor.fetchone()[0]
    avg_rating_text = f"{avg_rating:.1f} ⭐" if avg_rating else "Нет оценок"

    profile_text = (
        f"<b>👤 Профиль</b>
"
        f"🆔 ID: <code>{user_id}</code>
"
        f"🏷 Имя: {username}
"
        f"⭐ Рейтинг: {avg_rating_text}
"
        f"✅ Выполнено заданий: {completed}
"
        f"📌 Размещено заданий: {posted}"
    )

    await message.answer(profile_text, parse_mode="HTML")



@dp.callback_query_handler(lambda c: c.data.startswith("finish_"))
async def finish_task(callback_query: types.CallbackQuery, state: FSMContext):
    task_id = int(callback_query.data.split("_")[1])

    # Найти исполнителя из откликов (предположим, что первый отклик - выбранный)
    cursor.execute("SELECT user_id FROM responses WHERE task_id = ?", (task_id,))
    result = cursor.fetchone()
    if result:
        performer_id = result[0]
        await state.update_data(performer_id=performer_id)
        await bot.send_message(callback_query.from_user.id, "Оцените исполнителя от 1 до 5:")
        await TaskForm.rate.set()
    else:
        await bot.send_message(callback_query.from_user.id, "Нет откликов, завершение невозможно.")

@dp.message_handler(state=TaskForm.rate)
async def give_rating(message: types.Message, state: FSMContext):
    try:
        rating = int(message.text)
        if rating < 1 or rating > 5:
            raise ValueError
    except ValueError:
        await message.reply("Пожалуйста, введите число от 1 до 5.")
        return

    data = await state.get_data()
    performer_id = data["performer_id"]

    cursor.execute("INSERT INTO ratings (user_id, rating) VALUES (?, ?)", (performer_id, rating))
    conn.commit()

    await message.answer("Спасибо! Вы оценили исполнителя.", reply_markup=main_kb)
    await state.finish()



@dp.message_handler(content_types=ContentType.PHOTO, state=TaskForm.description)
async def task_description_with_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await message.answer("Теперь введите описание задания (текст):")

@dp.message_handler(state=TaskForm.description)
async def task_description_text(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await TaskForm.budget.set()
    await message.answer("Введите бюджет задания:")



@dp.callback_query_handler(lambda c: c.data.startswith("chat_"))
async def start_chat(callback_query: types.CallbackQuery, state: FSMContext):
    partner_id = int(callback_query.data.split("_")[1])
    await state.update_data(partner_id=partner_id)
    await ChatForm.waiting_message.set()
    await bot.send_message(callback_query.from_user.id, "Напишите сообщение исполнителю:")

@dp.message_handler(state=ChatForm.waiting_message)
async def send_chat_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    partner_id = data["partner_id"]
    await bot.send_message(partner_id, f"💬 Сообщение от @{message.from_user.username or message.from_user.id}:
{message.text}")
    await message.answer("Сообщение отправлено!", reply_markup=main_kb)
    await state.finish()



@dp.callback_query_handler(lambda c: c.data.startswith("assign_"))
async def assign_executor(callback_query: types.CallbackQuery):
    _, task_id, executor_id = callback_query.data.split("_")
    task_id = int(task_id)
    executor_id = int(executor_id)
    cursor.execute("UPDATE tasks SET executor_id = ?, status = 'в процессе' WHERE id = ? AND user_id = ?", (executor_id, task_id, callback_query.from_user.id))
    conn.commit()
    await bot.send_message(executor_id, f"🎉 Вас назначили исполнителем задания #{task_id}!")
    await bot.answer_callback_query(callback_query.id, text="Исполнитель назначен.")



class RateForm(StatesGroup):
    task_id = State()
    executor_id = State()
    rating = State()

@dp.callback_query_handler(lambda c: c.data.startswith("complete_"))
async def complete_task(callback_query: types.CallbackQuery, state: FSMContext):
    task_id = int(callback_query.data.split("_")[1])
    cursor.execute("SELECT executor_id FROM tasks WHERE id = ? AND user_id = ?", (task_id, callback_query.from_user.id))
    row = cursor.fetchone()
    if row and row[0]:
        executor_id = row[0]
        cursor.execute("UPDATE tasks SET status = 'завершено' WHERE id = ?", (task_id,))
        conn.commit()
        await state.update_data(task_id=task_id, executor_id=executor_id)
        await RateForm.rating.set()
        await bot.send_message(callback_query.from_user.id, "Поставьте оценку исполнителю от 1 до 5:")
    else:
        await bot.answer_callback_query(callback_query.id, text="Нельзя завершить задание без исполнителя.", show_alert=True)

@dp.message_handler(state=RateForm.rating)
async def rate_executor(message: types.Message, state: FSMContext):
    try:
        rating = int(message.text)
        if rating < 1 or rating > 5:
            raise ValueError
    except ValueError:
        await message.answer("Введите число от 1 до 5.")
        return

    data = await state.get_data()
    executor_id = data["executor_id"]
    # Обновим рейтинг исполнителя (простое среднее)
    cursor.execute("SELECT rating, votes FROM users WHERE user_id = ?", (executor_id,))
    row = cursor.fetchone()
    if row:
        prev_rating, votes = row
        new_rating = (prev_rating * votes + rating) / (votes + 1)
        cursor.execute("UPDATE users SET rating = ?, votes = votes + 1 WHERE user_id = ?", (new_rating, executor_id))
    else:
        cursor.execute("INSERT INTO users (user_id, rating, votes) VALUES (?, ?, 1)", (executor_id, rating))
    conn.commit()
    await message.answer("Спасибо за оценку!", reply_markup=main_kb)
    await bot.send_message(executor_id, f"🎉 Задание завершено! Вам поставили оценку: {rating}/5")
    await state.finish()



@dp.message_handler(commands=["профиль"])
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT rating, votes FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        rating, votes = row
        await message.answer(f"👤 Ваш профиль:
Рейтинг: {rating:.2f} ⭐️
Голосов: {votes}")
    else:
        await message.answer("У вас пока нет рейтинга.")



@dp.callback_query_handler(lambda c: c.data.startswith("profile_"))
async def show_executor_profile(callback_query: types.CallbackQuery):
    executor_id = int(callback_query.data.split("_")[1])
    cursor.execute("SELECT rating, votes FROM users WHERE user_id = ?", (executor_id,))
    row = cursor.fetchone()
    if row:
        rating, votes = row
        text = f"👤 Профиль исполнителя {executor_id}:
Рейтинг: {rating:.2f} ⭐️
Голосов: {votes}"
    else:
        text = f"👤 Профиль исполнителя {executor_id}:
Пока нет рейтинга."
    await bot.send_message(callback_query.from_user.id, text)
    await bot.answer_callback_query(callback_query.id)
