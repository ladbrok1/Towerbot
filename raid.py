############################
### raid.py - Групповые рейды ###
############################
"""
Модуль групповых рейдов:
- Поиск группы
- Создание группы
- Рейды на боссов
- Эпические боссы
- Распределение добычи
"""
import random
import database as db
import world
from telebot import types

def attack_boss(bot, message):
    player_id = message.from_user.id
    player_data = db.load_player(player_id)
    if player_data is None:
        bot.send_message(message.chat.id, "❌ Ошибка загрузки данных! Попробуй перезапустить бота командой /start")
        return

    server_progress = db.get_server_progress()

    if player_data["floor"] != server_progress["current_floor"]:
        bot.send_message(
            message.chat.id,
            f"❌ Босс доступен только на текущем серверном этаже ({server_progress['current_floor']})!\n"
            f"Ты находишься на этаже {player_data['floor']}.",
            parse_mode="Markdown"
        )
        return

    if player_data["state"] != "idle":
        bot.send_message(message.chat.id, "❌ Ты уже в бою!")
        return

    boss_data = world.bosses_data.get(server_progress["current_floor"], world.bosses_data[1])
    boss = boss_data.copy()
    boss["hp"] = server_progress["boss_hp"]  # Используем текущее HP босса

    # Проверка на силу игрока
    if player_data["level"] < boss["min_level"]:
        bot.send_message(
            message.chat.id,
            f"⚠️ *Внимание!*\nБосс слишком силен для тебя!\n"
            f"Твой уровень: {player_data['level']} | Требуется: {boss['min_level']}+\n\n"
            "Найди группу или стань сильнее!",
            parse_mode="Markdown"
        )
        return

    player_data["state"] = "fighting"
    player_data["current_enemy"] = boss
    db.save_player(player_id, player_data)

    # Создаем клавиатуру для боя
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    weapon = player_data["current_weapon"]
    skills = player_data["weapons"][weapon]["skills"]

    markup.add(f"⚔️ Атаковать ({world.weapons_data[weapon]['base_skill']})")
    for skill in skills[1:]:
        markup.add(f"🔮 {skill}")

    if "health_potion" in player_data["inventory"]:
        markup.add("💉 Зелье здоровья")

    markup.add("🏃 Бежать")

    floor_desc = world.FLOOR_DESCRIPTIONS.get(player_data["floor"], f"Этаж {player_data['floor']}")
    bot.send_message(
        message.chat.id,
        f"👑 *На {floor_desc} ты вступаешь в бой с {boss['name']}!*\n"
        f"{boss['description']}\n\n"
        f"❤️ HP: {boss['hp']}/{boss_data['max_hp']} | 💢 Урон: {boss['damage']}\n\n"
        "Выбери действие:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

def raid_menu(bot, message):
    player_id = message.from_user.id
    player_data = db.load_player(player_id)

    if not player_data:
        return

    server_progress = db.get_server_progress()
    boss_data = world.bosses_data.get(server_progress["current_floor"], world.bosses_data[1])

    markup = types.InlineKeyboardMarkup()

    # Кнопка поиска группы
    markup.add(types.InlineKeyboardButton("🔍 Найти группу", callback_data="find_group"))

    # Кнопка создания группы
    markup.add(types.InlineKeyboardButton("👥 Создать группу", callback_data="create_group"))

    # Кнопка вызова эпического босса
    if "boss_key" in player_data["inventory"]:
        markup.add(types.InlineKeyboardButton(
            "💀 Вызвать эпического босса",
            callback_data="summon_epic_boss"
        ))

    raid_info = (
        f"👑 *Рейд на босса этажа {server_progress['current_floor']}*\n"
        f"Босс: {boss_data['name']}\n"
        f"Здоровье: {server_progress['boss_hp']}/{boss_data['max_hp']}\n\n"
        f"Группы, идущие в рейд:"
    )

    # TODO: Добавить список активных групп

    bot.send_message(
        message.chat.id,
        raid_info,
        reply_markup=markup,
        parse_mode="Markdown"
    )

def handle_raid(bot, call):
    # Обработка действий рейда
    action = call.data.split("_")[1]

    if action == "find_group":
        find_group(bot, call)
    elif action == "create_group":
        create_group(bot, call)
    elif action == "summon_epic":
        summon_epic_boss(bot, call)

def find_group(bot, call):
    player_id = call.from_user.id
    player_data = db.load_player(player_id)

    # Поиск доступных групп
    # ...

    bot.answer_callback_query(call.id, "🔍 Поиск группы...")

def create_group(bot, call):
    player_id = call.from_user.id
    player_data = db.load_player(player_id)

    # Создание новой группы
    # ...

    bot.answer_callback_query(call.id, "👥 Группа создана!")

def summon_epic_boss(bot, call):
    player_id = call.from_user.id
    player_data = db.load_player(player_id)

    if "boss_key" not in player_data["inventory"]:
        bot.answer_callback_query(call.id, "❌ У тебя нет ключа босса!")
        return

    # Выбираем случайного эпического босса
    epic_boss = random.choice(list(world.epic_bosses.values()))

    # Убираем ключ
    player_data["inventory"].remove("boss_key")
    db.save_player(player_id, player_data)

    # Создаем рейд
    # ...

    bot.answer_callback_query(call.id, f"💀 Ты вызвал {epic_boss['name']}!")