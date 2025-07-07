import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_states = {}  # user_id: dict

def get_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Создать группу"))
    kb.add(KeyboardButton("Мои группы"))
    return kb

def get_back_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Назад"))
    return kb

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_states[message.from_user.id] = {}
    await message.reply(
        "Привет! 👋\nЯ помогу создавать группы с твоими картинками.\nВыбери действие:",
        reply_markup=get_main_menu()
    )

@dp.message_handler(lambda msg: msg.text == "Создать группу")
async def ask_group_name(message: types.Message):
    user_states[message.from_user.id] = {'step': 'create_group'}
    await message.reply("Введи название для новой группы:", reply_markup=get_back_menu())

@dp.message_handler(lambda msg: msg.text == "Назад")
async def back_to_main(message: types.Message):
    user_states[message.from_user.id] = {}
    await message.reply("Главное меню", reply_markup=get_main_menu())

@dp.message_handler(lambda msg: msg.text == "Мои группы")
async def show_groups(message: types.Message):
    user_id = str(message.from_user.id)
    groups_dir = f'images/{user_id}'
    if not os.path.exists(groups_dir) or not os.listdir(groups_dir):
        await message.reply("У тебя нет ни одной группы.", reply_markup=get_main_menu())
        return
    groups = os.listdir(groups_dir)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for g in groups:
        kb.add(KeyboardButton(g))
    kb.add(KeyboardButton("Назад"))
    user_states[message.from_user.id] = {'step': 'choose_group'}
    await message.reply("Твои группы:", reply_markup=kb)

@dp.message_handler(lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'create_group')
async def create_group(message: types.Message):
    group_name = message.text.strip()
    if not group_name.isalnum():
        await message.reply("Название группы должно содержать только буквы и цифры. Введи снова:")
        return
    user_id = str(message.from_user.id)
    os.makedirs(f'images/{user_id}/{group_name}', exist_ok=True)
    user_states[message.from_user.id] = {'step': 'wait_image', 'group': group_name}
    await message.reply(
        f"Группа '{group_name}' создана! Теперь отправь картинку, чтобы добавить её в эту группу.",
        reply_markup=get_back_menu()
    )

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    state = user_states.get(message.from_user.id)
    if not state or state.get('step') != 'wait_image':
        await message.reply("Для добавления картинки сначала создай группу.", reply_markup=get_main_menu())
        return
    group = state['group']
    user_id = str(message.from_user.id)
    # Сохраняем фото временно
    os.makedirs(f'images/{user_id}/{group}', exist_ok=True)
    photo = message.photo[-1]
    temp_path = f'images/{user_id}/{group}/temp.jpg'
    await photo.download(destination_file=temp_path)
    user_states[message.from_user.id].update({'step': 'wait_image_name', 'temp_path': temp_path})
    await message.reply("Как назвать это изображение? (Только буквы/цифры)", reply_markup=get_back_menu())

@dp.message_handler(lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'wait_image_name')
async def set_image_name(message: types.Message):
    name = message.text.strip()
    if not name.isalnum():
        await message.reply("Имя картинки должно содержать только буквы и цифры. Введи снова:")
        return
    state = user_states[message.from_user.id]
    group = state['group']
    user_id = str(message.from_user.id)
    temp_path = state['temp_path']
    new_path = f'images/{user_id}/{group}/{name}.jpg'
    os.rename(temp_path, new_path)
    await message.reply(
        f"Изображение '{name}' добавлено в группу '{group}'!\nОтправь ещё картинку или нажми 'Назад'.",
        reply_markup=get_back_menu()
    )
    user_states[message.from_user.id]['step'] = 'wait_image'
    user_states[message.from_user.id].pop('temp_path', None)

@dp.message_handler(lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'choose_group')
async def choose_group(message: types.Message):
    group = message.text.strip()
    user_id = str(message.from_user.id)
    group_path = f'images/{user_id}/{group}'
    if not os.path.exists(group_path):
        await message.reply("Группа не найдена.", reply_markup=get_main_menu())
        user_states[message.from_user.id] = {}
        return
    images = [img for img in os.listdir(group_path) if img.endswith('.jpg')]
    if not images:
        await message.reply("В группе нет картинок.", reply_markup=get_back_menu())
        return
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for img in images:
        kb.add(KeyboardButton(img.rsplit('.', 1)[0]))
    kb.add(KeyboardButton("Назад"))
    user_states[message.from_user.id] = {'step': 'show_image', 'group': group}
    await message.reply(f"Картинки в группе '{group}':", reply_markup=kb)

@dp.message_handler(lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'show_image')
async def send_image(message: types.Message):
    image_name = message.text.strip()
    state = user_states[message.from_user.id]
    group = state['group']
    user_id = str(message.from_user.id)
    image_path = f'images/{user_id}/{group}/{image_name}.jpg'
    if not os.path.exists(image_path):
        await message.reply("Картинка не найдена.", reply_markup=get_back_menu())
        return
    with open(image_path, 'rb') as photo:
        await bot.send_photo(message.chat.id, photo, caption=f"Картинка '{image_name}' из группы '{group}'")
    # Можно добавить опции "Удалить" и т.д.

if __name__ == "__main__":
    os.makedirs("images", exist_ok=True)
    executor.start_polling(dp, skip_updates=True)
