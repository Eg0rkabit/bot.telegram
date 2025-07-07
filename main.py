import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv
from aiogram.utils.exceptions import TelegramAPIError
from aiogram.utils.exceptions import MessageNotModified

@dp.callback_query_handler(lambda call: call.data.startswith("groups_"))
async def show_groups(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    page = int(call.data.split("_")[1])
    groups_dir = f'images/{user_id}'
    groups = sorted(os.listdir(groups_dir)) if os.path.exists(groups_dir) else []
    total = len(groups)
    groups_on_page = groups[page*GROUPS_PER_PAGE:(page+1)*GROUPS_PER_PAGE]
    if not groups:
        try:
            await call.message.edit_text("У тебя нет ни одной группы!", reply_markup=main_menu_kb())
        except MessageNotModified:
            pass
        return
    try:
        await call.message.edit_text(
            "<b>Твои группы:</b>",
            parse_mode="HTML",
            reply_markup=groups_kb(groups_on_page, page, total)
        )
    except MessageNotModified:
        pass

@dp.errors_handler()
async def global_error_handler(update, exception):
    logging.exception(f'Произошла ошибка: {exception}')
    return True  # Ошибку обработали, бот не падает

logging.basicConfig(level=logging.INFO)
load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_states = {}
GROUPS_PER_PAGE = 5
IMAGES_PER_PAGE = 5

def main_menu_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🗂 Мои группы", callback_data="groups_0"),
        InlineKeyboardButton("➕ Создать группу", callback_data="create_group"),
        InlineKeyboardButton("🔍 Поиск картинки", callback_data="search_img")
    )
    return kb

def groups_kb(groups, page, total):
    kb = InlineKeyboardMarkup(row_width=3)
    for g in groups:
        kb.row(
            InlineKeyboardButton(f"📁 {g}", callback_data=f"open_group:{g}:0"),
            InlineKeyboardButton("✏️", callback_data=f"rename_group:{g}"),
            InlineKeyboardButton("❌", callback_data=f"delete_group:{g}"),
        )
        kb.add(InlineKeyboardButton("🔗 Поделиться", callback_data=f"share_group:{g}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("←", callback_data=f"groups_{page-1}"))
    if (page+1)*GROUPS_PER_PAGE < total:
        nav.append(InlineKeyboardButton("→", callback_data=f"groups_{page+1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton("🔙 В меню", callback_data="back_main"))
    return kb

def images_kb(images, group, page, total):
    kb = InlineKeyboardMarkup(row_width=3)
    for img in images:
        kb.row(
            InlineKeyboardButton(f"🖼 {img}", callback_data=f"show_img:{group}:{img}"),
            InlineKeyboardButton("✏️", callback_data=f"rename_img:{group}:{img}"),
            InlineKeyboardButton("❌", callback_data=f"delete_img:{group}:{img}")
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("←", callback_data=f"open_group:{group}:{page-1}"))
    if (page+1)*IMAGES_PER_PAGE < total:
        nav.append(InlineKeyboardButton("→", callback_data=f"open_group:{group}:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.row(
        InlineKeyboardButton("⬆️ Добавить", callback_data=f"add_img:{group}"),
        InlineKeyboardButton("🔙 К группам", callback_data="groups_0")
    )
    return kb

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_states[message.from_user.id] = {}
    args = message.get_args()
    if args and args.startswith("share_"):
        group = args.split("share_", 1)[1]
        user_id = str(message.from_user.id)
        group_path = f"images/{user_id}/{group}"
        if not os.path.exists(group_path):
            await message.reply("Группа не найдена.", reply_markup=main_menu_kb())
            return
        images = sorted([img[:-4] for img in os.listdir(group_path) if img.endswith('.jpg')])
        for img in images:
            with open(f"images/{user_id}/{group}/{img}.jpg", "rb") as f:
                await message.reply_photo(f, caption=f"<b>{img}</b> из <b>{group}</b>", parse_mode="HTML")
        return
    text = (
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Я — твой фото-органайзер!\n\n"
        "• Создавай <b>группы</b>\n"
        "• Загружай <b>фото</b>\n"
        "• <b>Переименовывай</b> и <b>удаляй</b> что угодно!\n"
        "• Всё управление — через удобные кнопки 👇"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())

@dp.callback_query_handler(lambda call: call.data.startswith("back_main"))
async def back_main(call: types.CallbackQuery):
    user_states[call.from_user.id] = {}
    await call.message.edit_text("Главное меню:", reply_markup=main_menu_kb())

@dp.callback_query_handler(lambda call: call.data.startswith("groups_"))
async def show_groups(call: types.CallbackQuery):
    user_id = str(call.from_user.id)
    page = int(call.data.split("_")[1])
    groups_dir = f'images/{user_id}'
    groups = sorted(os.listdir(groups_dir)) if os.path.exists(groups_dir) else []
    total = len(groups)
    groups_on_page = groups[page*GROUPS_PER_PAGE:(page+1)*GROUPS_PER_PAGE]
    if not groups:
        await call.message.edit_text("У тебя нет ни одной группы!", reply_markup=main_menu_kb())
        return
    await call.message.edit_text(
        "<b>Твои группы:</b>",
        parse_mode="HTML",
        reply_markup=groups_kb(groups_on_page, page, total)
    )

@dp.callback_query_handler(lambda call: call.data == "create_group")
async def create_group_start(call: types.CallbackQuery):
    user_states[call.from_user.id] = {"await": "create_group"}
    await call.message.edit_text("Введи название для новой группы (только буквы/цифры):",
                                 reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 В меню", callback_data="back_main")))

@dp.message_handler(lambda msg: user_states.get(msg.from_user.id, {}).get("await") == "create_group")
async def create_group_finish(message: types.Message):
    group_name = message.text.strip()
    if not group_name.isalnum():
        await message.reply("Название должно быть только из букв и цифр. Попробуй снова:")
        return
    user_id = str(message.from_user.id)
    path = f'images/{user_id}/{group_name}'
    if os.path.exists(path):
        await message.reply("Группа с таким названием уже есть. Введи другое:")
        return
    os.makedirs(path, exist_ok=True)
    user_states[message.from_user.id] = {}
    await message.reply(f"Группа <b>{group_name}</b> создана!", parse_mode="HTML", reply_markup=main_menu_kb())

@dp.callback_query_handler(lambda call: call.data.startswith("delete_group:"))
async def delete_group_ask(call: types.CallbackQuery):
    group = call.data.split(":")[1]
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Да", callback_data=f"confirm_delete_group:{group}"),
        InlineKeyboardButton("❌ Нет", callback_data="groups_0")
    )
    await call.message.edit_text(f"Удалить группу <b>{group}</b> вместе со всеми фото?", parse_mode="HTML", reply_markup=kb)

@dp.callback_query_handler(lambda call: call.data.startswith("confirm_delete_group:"))
async def delete_group_confirm(call: types.CallbackQuery):
    group = call.data.split(":")[1]
    user_id = str(call.from_user.id)
    group_path = f'images/{user_id}/{group}'
    if os.path.exists(group_path):
        import shutil
        shutil.rmtree(group_path)
    await call.message.edit_text(f"Группа <b>{group}</b> удалена.", parse_mode="HTML", reply_markup=main_menu_kb())

@dp.callback_query_handler(lambda call: call.data.startswith("rename_group:"))
async def rename_group_start(call: types.CallbackQuery):
    group = call.data.split(":")[1]
    user_states[call.from_user.id] = {"await": "rename_group", "group": group}
    await call.message.edit_text(f"Введи новое название для группы <b>{group}</b> (только буквы/цифры):", parse_mode="HTML")

@dp.message_handler(lambda msg: user_states.get(msg.from_user.id, {}).get("await") == "rename_group")
async def rename_group_finish(message: types.Message):
    state = user_states[message.from_user.id]
    old_name = state["group"]
    new_name = message.text.strip()
    if not new_name.isalnum():
        await message.reply("Название должно быть только из букв и цифр. Попробуй снова:")
        return
    user_id = str(message.from_user.id)
    old_path = f'images/{user_id}/{old_name}'
    new_path = f'images/{user_id}/{new_name}'
    if os.path.exists(new_path):
        await message.reply("Группа с таким названием уже есть. Введи другое:")
        return
    os.rename(old_path, new_path)
    user_states[message.from_user.id] = {}
    await message.reply(f"Группа <b>{old_name}</b> переименована в <b>{new_name}</b>!", parse_mode="HTML", reply_markup=main_menu_kb())

@dp.callback_query_handler(lambda call: call.data.startswith("open_group:"))
async def open_group(call: types.CallbackQuery):
    parts = call.data.split(":")
    group = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0
    user_id = str(call.from_user.id)
    group_path = f'images/{user_id}/{group}'
    images = sorted([img[:-4] for img in os.listdir(group_path) if img.endswith('.jpg')]) if os.path.exists(group_path) else []
    total = len(images)
    images_on_page = images[page*IMAGES_PER_PAGE:(page+1)*IMAGES_PER_PAGE]
    if not images:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("⬆️ Добавить", callback_data=f"add_img:{group}"),
            InlineKeyboardButton("🔙 К группам", callback_data="groups_0")
        )
        await call.message.edit_text(f"В группе <b>{group}</b> нет картинок.", parse_mode="HTML", reply_markup=kb)
        return
    await call.message.edit_text(
        f"<b>Картинки в группе <u>{group}</u>:</b>",
        parse_mode="HTML",
        reply_markup=images_kb(images_on_page, group, page, total)
    )

@dp.callback_query_handler(lambda call: call.data == "search_img")
async def search_image_start(call: types.CallbackQuery):
    user_states[call.from_user.id] = {"await": "search_img"}
    await call.message.edit_text("Введи название картинки для поиска:",
                                 reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 В меню", callback_data="back_main")))

@dp.message_handler(lambda msg: user_states.get(msg.from_user.id, {}).get("await") == "search_img")
async def search_image_finish(message: types.Message):
    query = message.text.strip().lower()
    if len(query) < 2:
        await message.reply("Слишком короткий запрос. Введи хотя бы 2 символа.")
        return
    user_id = str(message.from_user.id)
    found = []
    base_path = f"images/{user_id}"
    for group in os.listdir(base_path):
        group_path = os.path.join(base_path, group)
        for img in os.listdir(group_path):
            if img.endswith('.jpg') and query in img.lower():
                found.append((group, img))
    if not found:
        await message.reply("Картинок не найдено.", reply_markup=main_menu_kb())
        user_states[message.from_user.id] = {}
        return
    for group, img in found:
        with open(f"images/{user_id}/{group}/{img}", "rb") as f:
            await message.reply_photo(f, caption=f"<b>{img[:-4]}</b> в группе <b>{group}</b>", parse_mode="HTML")
    user_states[message.from_user.id] = {}

@dp.callback_query_handler(lambda call: call.data.startswith("add_img:"))
async def add_image_start(call: types.CallbackQuery):
    group = call.data.split(":")[1]
    user_states[call.from_user.id] = {"await": "add_img", "group": group}
    await call.message.edit_text("Отправь фото для добавления в группу.", parse_mode="HTML")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def add_image_photo(message: types.Message):
    state = user_states.get(message.from_user.id)
    if not state or state.get("await") != "add_img":
        return
    group = state["group"]
    user_id = str(message.from_user.id)
    group_path = f'images/{user_id}/{group}'
    os.makedirs(group_path, exist_ok=True)
    photo = message.photo[-1]
    temp_path = f"{group_path}/temp.jpg"
    await photo.download(destination_file=temp_path)
    user_states[message.from_user.id].update({"await": "add_img_name", "temp_path": temp_path})
    await message.reply("Введи имя для картинки (только буквы/цифры):")

@dp.message_handler(lambda msg: user_states.get(msg.from_user.id, {}).get("await") == "add_img_name")
async def add_image_rename(message: types.Message):
    name = message.text.strip()
    if not name.isalnum():
        await message.reply("Имя должно быть только из букв и цифр. Введи снова:")
        return
    state = user_states[message.from_user.id]
    group = state["group"]
    user_id = str(message.from_user.id)
    temp_path = state["temp_path"]
    new_path = f"images/{user_id}/{group}/{name}.jpg"
    os.rename(temp_path, new_path)
    user_states[message.from_user.id] = {}
    await message.reply(f"Фото <b>{name}</b> добавлено в группу <b>{group}</b>!", parse_mode="HTML", reply_markup=main_menu_kb())

@dp.callback_query_handler(lambda call: call.data.startswith("show_img:"))
async def show_img(call: types.CallbackQuery):
    parts = call.data.split(":")
    group, image = parts[1], parts[2]
    user_id = str(call.from_user.id)
    image_path = f"images/{user_id}/{group}/{image}.jpg"
    if not os.path.exists(image_path):
        await call.answer("Файл не найден", show_alert=True)
        return
    with open(image_path, "rb") as f:
        await bot.send_photo(call.message.chat.id, f, caption=f"Картинка <b>{image}</b> из <b>{group}</b>", parse_mode="HTML")

@dp.callback_query_handler(lambda call: call.data.startswith("delete_img:"))
async def delete_img_ask(call: types.CallbackQuery):
    parts = call.data.split(":")
    group, image = parts[1], parts[2]
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Да", callback_data=f"confirm_delete_img:{group}:{image}"),
        InlineKeyboardButton("❌ Нет", callback_data=f"open_group:{group}:0")
    )
    await call.message.edit_text(f"Удалить картинку <b>{image}</b> из <b>{group}</b>?", parse_mode="HTML", reply_markup=kb)

@dp.callback_query_handler(lambda call: call.data.startswith("confirm_delete_img:"))
async def delete_img_confirm(call: types.CallbackQuery):
    parts = call.data.split(":")
    group, image = parts[1], parts[2]
    user_id = str(call.from_user.id)
    image_path = f"images/{user_id}/{group}/{image}.jpg"
    if os.path.exists(image_path):
        os.remove(image_path)
    await call.message.edit_text(f"Картинка <b>{image}</b> удалена!", parse_mode="HTML", reply_markup=main_menu_kb())

@dp.callback_query_handler(lambda call: call.data.startswith("rename_img:"))
async def rename_img_start(call: types.CallbackQuery):
    parts = call.data.split(":")
    group, image = parts[1], parts[2]
    user_states[call.from_user.id] = {"await": "rename_img", "group": group, "old_name": image}
    await call.message.edit_text(f"Введи новое имя для картинки <b>{image}</b> (только буквы/цифры):", parse_mode="HTML")

@dp.message_handler(lambda msg: user_states.get(msg.from_user.id, {}).get("await") == "rename_img")
async def rename_img_finish(message: types.Message):
    state = user_states[message.from_user.id]
    group = state["group"]
    old_name = state["old_name"]
    new_name = message.text.strip()
    if not new_name.isalnum():
        await message.reply("Имя должно быть только из букв и цифр. Попробуй снова:")
        return
    user_id = str(message.from_user.id)
    old_path = f"images/{user_id}/{group}/{old_name}.jpg"
    new_path = f"images/{user_id}/{group}/{new_name}.jpg"
    if os.path.exists(new_path):
        await message.reply("Картинка с таким именем уже есть. Введи другое:")
        return
    os.rename(old_path, new_path)
    user_states[message.from_user.id] = {}
    await message.reply(f"Картинка <b>{old_name}</b> переименована в <b>{new_name}</b>!", parse_mode="HTML", reply_markup=main_menu_kb())

@dp.callback_query_handler(lambda call: call.data.startswith("share_group:"))
async def share_group(call: types.CallbackQuery):
    group = call.data.split(":")[1]
    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=share_{group}"
    await call.message.answer(f"🔗 Ссылка для доступа к группе <b>{group}</b>:\n{link}", parse_mode="HTML")

if __name__ == "__main__":
    os.makedirs("images", exist_ok=True)
    executor.start_polling(dp, skip_updates=True)
