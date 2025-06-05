############################
### player.py - Управление игроком ###
############################
"""
Модуль управления игроком:
- Создание персонажа
- Управление характеристиками
- Инвентарь и предметы
- Смерть и возрождение
- Взаимодействие с гильдиями
"""
import random
import database as db
import world
from telebot import types

def handle_start(bot, message):
    player_id = message.from_user.id
    player = db.load_player(player_id)

    if not player:
        # Новый игрок
        bot.send_message(message.chat.id, world.world_lore, parse_mode="Markdown")
        bot.send_message(message.chat.id,
                        "🌠 *Добро пожаловать в Башню Тысячи Грез!*\n"
                        "Прежде чем начать, скажи мне, как тебя зовут, искатель приключений?",
                        parse_mode="Markdown")
        # Исправление: передаем bot в следующую функцию
        bot.register_next_step_handler(message, lambda m: set_nickname(bot, m))
    else:
        # Возвращение игрока
        show_main_menu(bot, message)

def set_nickname(bot, message):  # Добавлен параметр bot
    player_id = message.from_user.id
    player = world.player_template.copy()
    player["nickname"] = message.text

    db.save_player(player_id, player)

    bot.send_message(message.chat.id,
                    "🎲 *Распредели 25 очков характеристик:* (формат: 5 5 5 5 5 5)\n"
                    "💪 Сила - увеличивает урон и шанс критического удара\n"
                    "🏃 Ловкость - увеличивает шанс уклонения и скорость атаки\n"
                    "❤️ Живучесть - увеличивает здоровье\n"
                    "🍀 Удача - увеличивает шанс найти редкие предметы\n"
                    "🎯 Точность - увеличивает шанс попадания\n"
                    "🛡️ Защита - уменьшает получаемый урон",
                    parse_mode="Markdown")
    # Исправление: передаем bot в следующую функцию
    bot.register_next_step_handler(message, lambda m: set_stats(bot, m))

def set_stats(bot, message):  # Добавлен параметр bot
    player_id = message.from_user.id
    player = db.load_player(player_id)

    try:
        stats = list(map(int, message.text.split()))
        if sum(stats) == 25 and len(stats) == 6:
            player["stats"] = {
                "strength": stats[0],
                "agility": stats[1],
                "vitality": stats[2],
                "luck": stats[3],
                "accuracy": stats[4],
                "defense": stats[5]
            }
            player["max_hp"] = 80 + stats[2] * 4
            player["hp"] = player["max_hp"]

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            weapons = ["🗡️ Меч", "🔪 Кинжал", "🏏 Булава", "🏹 Лук", "🪓 Топор", "🔱 Копье", "🔨 Молот", "🏹 Арбалет"]
            markup.add(*weapons[:4])
            markup.add(*weapons[4:])

            bot.send_message(message.chat.id,
                           "⚔️ *Выбери свое начальное оружие:*\n"
                           "🗡️ Меч - сбалансированное оружие\n"
                           "🔪 Кинжал - быстрые атаки\n"
                           "🏏 Булава - мощные удары\n"
                           "🏹 Лук - дальний бой\n"
                           "🪓 Топор - высокий урон\n"
                           "🔱 Копье - дальние атаки\n"
                           "🔨 Молот - сокрушительные удары\n"
                           "🏹 Арбалет - мощные выстрелы",
                           reply_markup=markup, parse_mode="Markdown")
            # Исправление: передаем bot в следующую функцию
            bot.register_next_step_handler(message, lambda m: set_weapon(bot, m))

            db.save_player(player_id, player)
        else:
            raise ValueError
    except:
        bot.send_message(message.chat.id, "❌ Ошибка! Введи 6 чисел (сумма=25).")
        bot.register_next_step_handler(message, lambda m: set_stats(bot, m))

def set_weapon(bot, message):  # Добавлен параметр bot
    player_id = message.from_user.id
    player = db.load_player(player_id)

    if player is None:
        bot.send_message(message.chat.id, "❌ Ошибка создания персонажа! Попробуй снова.")
        return

    weapon_choice = {
        "🗡️ Меч": "sword",
        "🔪 Кинжал": "dagger",
        "🏏 Булава": "mace",
        "🏹 Лук": "bow",
        "🪓 Топор": "axe",
        "🔱 Копье": "spear",
        "🔨 Молот": "hammer",
        "🏹 Арбалет": "crossbow"
    }

    if message.text in weapon_choice:
        weapon = weapon_choice[message.text]

        # Проверка существования оружия в словаре
        if weapon not in world.weapons_data:
            bot.send_message(message.chat.id, f"❌ Ошибка конфигурации: оружие {weapon} не найдено!")
            return

        player["current_weapon"] = weapon
        player["weapons"][weapon]["level"] = 1
        player["weapons"][weapon]["skills"].append(world.weapons_data[weapon]["base_skill"])

        # Проверяем новые навыки
        check_new_skills(bot, player_id, weapon)

        db.save_player(player_id, player)

        bot.send_message(message.chat.id,
                        f"✅ Ты выбрал {world.weapons_data[weapon]['name']}!\n"
                        f"Твой первый навык: *{world.weapons_data[weapon]['base_skill']}*",
                        parse_mode="Markdown")
        show_main_menu(bot, message)
    else:
        bot.send_message(message.chat.id, "❌ Выбери оружие из списка!")
        bot.register_next_step_handler(message, lambda m: set_weapon(bot, m))

def check_new_skills(bot, player_id, weapon_type):
    player = db.load_player(player_id)
    if player is None:
        return

    weapon_data = world.weapons_data[weapon_type]
    stats = player["stats"]

    # Определяем доминирующую характеристику
    dominant_stat = max(stats, key=stats.get)
    stat_value = stats[dominant_stat]

    # Выбираем подходящие навыки
    available_skills = []
    for skill_name, skill_data in weapon_data["skills"].items():
        # Проверяем требования для навыка
        req_met = True
        for stat, value in skill_data.items():
            if stat.startswith("min_"):
                stat_name = stat[4:]
                if stats.get(stat_name, 0) < value:
                    req_met = False
                    break

        # Если требования выполнены и навык еще не получен
        if req_met and skill_name not in player["weapons"][weapon_type]["skills"]:
            # Предпочтение навыкам, соответствующим доминирующей характеристике
            if weapon_data["stat"] == dominant_stat:
                available_skills.insert(0, skill_name)  # Добавляем в начало
            else:
                available_skills.append(skill_name)

    # Если есть доступные навыки, выбираем случайный
    if available_skills:
        new_skill = random.choice(available_skills)
        player["weapons"][weapon_type]["skills"].append(new_skill)
        bot.send_message(player_id,
                       f"✨ Ты освоил новый навык: *{new_skill}*!\n"
                       f"Используй его в бою с помощью кнопки навыков.",
                       parse_mode="Markdown")
        db.save_player(player_id, player)

def show_main_menu(bot, message):
    player_id = message.from_user.id
    player = db.load_player(player_id)
    if player is None:
        bot.send_message(message.chat.id, "❌ Ошибка загрузки данных! Попробуй перезапустить бота командой /start")
        return

    server_progress = db.get_server_progress()
    floor_desc = world.FLOOR_DESCRIPTIONS.get(player["floor"], f"Этаж {player['floor']}")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        "⚔️ Атаковать моба",
        "🏃‍♂️ Исследовать",
        "👑 Атаковать босса",
        "👥 Рейды",
        "⚔️ PvP",
        "🛒 Магазин",
        "📊 Персонаж",
        "📦 Инвентарь",
        "🔧 Таланты",
        "🏦 Экономика",
        "🏰 Гильдия"
    ]
    markup.add(*buttons[:3])
    markup.add(*buttons[3:6])
    markup.add(*buttons[6:9])
    markup.add(*buttons[9:])

    # Опыт для следующего уровня
    required_exp = player['level'] * 100

    # Оружие
    weapon = player['current_weapon']
    if weapon:
        weapon_name = world.weapons_data[weapon]['name']
        weapon_level = player['weapons'][weapon]['level']
        weapon_text = f"🗡️ Оружие: {weapon_name} (Ур. {weapon_level})"
    else:
        weapon_text = "🗡️ Оружие: Не выбрано"

    status = (
        f"👤 *{player['nickname']}* | Ур. {player['level']} ({player['exp']}/{required_exp})\n"
        f"🏆 Этаж {player['floor']}: {floor_desc}\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
        f"🪙 Золото: {player['gold']}\n"
        f"{weapon_text}"
    )

    bot.send_message(message.chat.id, status, reply_markup=markup, parse_mode="Markdown")

def show_character(bot, message):
    player_id = message.from_user.id
    player = db.load_player(player_id)
    if player is None:
        bot.send_message(message.chat.id, "❌ Ошибка загрузки данных! Попробуй перезапустить бота командой /start")
        return

    weapon = player["current_weapon"]
    weapon_level = player["weapons"][weapon]["level"] if weapon else 0
    weapon_skills = ", ".join(player["weapons"][weapon]["skills"]) if weapon else "Нет навыков"

    stats = player["stats"]
    stat_info = (
        f"💪 Сила: {stats['strength']}\n"
        f"🏃 Ловкость: {stats['agility']}\n"
        f"❤️ Живучесть: {stats['vitality']}\n"
        f"🍀 Удача: {stats['luck']}\n"
        f"🎯 Точность: {stats['accuracy']}\n"
        f"🛡️ Защита: {stats['defense']}"
    )

    # Опыт для следующего уровня
    required_exp = player['level'] * 100

    character_info = (
        f"👤 *{player['nickname']}*\n"
        f"🏆 Уровень: {player['level']} ({player['exp']}/{required_exp} опыта)\n"
        f"🏠 Этаж: {player['floor']}\n"
        f"💀 Смертей: {player['deaths']}\n\n"
        f"⚔️ *Оружие:* {world.weapons_data[weapon]['name'] if weapon else 'Не выбрано'} (Ур. {weapon_level})\n"
        f"🔮 Навыки: {weapon_skills}\n\n"
        f"📊 *Характеристики:*\n{stat_info}"
    )

    markup = types.InlineKeyboardMarkup()
    if player["exp"] >= required_exp:
        markup.add(types.InlineKeyboardButton("⬆️ Повысить уровень", callback_data="level_up"))

    bot.send_message(message.chat.id, character_info, reply_markup=markup, parse_mode="Markdown")

def increase_stat(bot, call):
    player_id = call.from_user.id
    player = db.load_player(player_id)
    if player is None:
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки данных!")
        return

    stat_map = {
        "stat_str": "strength",
        "stat_agi": "agility",
        "stat_acc": "accuracy",
        "stat_luck": "luck",
        "stat_def": "defense",
        "stat_vit": "vitality"
    }

    stat = stat_map[call.data]
    player["stats"][stat] += 1

    # Обновляем производные характеристики
    if stat == "vitality":
        player["max_hp"] = 80 + player["stats"]["vitality"] * 4
        player["hp"] = min(player["hp"], player["max_hp"])

    db.save_player(player_id, player)

    bot.answer_callback_query(call.id, f"{stat} увеличен!")
    show_character(bot, call.message)

def show_inventory(bot, message):
    player_id = message.from_user.id
    player = db.load_player(player_id)
    if player is None:
        bot.send_message(message.chat.id, "❌ Ошибка загрузки данных! Попробуй перезапустить бота командой /start")
        return

    if not player["inventory"]:
        bot.send_message(message.chat.id, "Твой инвентарь пуст!")
        return

    inventory_text = "🎒 *Твой инвентарь:*\n"
    for item in player["inventory"]:
        inventory_text += f"- {item}\n"

    markup = types.InlineKeyboardMarkup()
    if "health_potion" in player["inventory"]:
        markup.add(types.InlineKeyboardButton("💉 Использовать зелье здоровья", callback_data="use_health_potion"))
    if "elixir_strength" in player["inventory"]:
        markup.add(types.InlineKeyboardButton("💪 Использовать эликсир силы", callback_data="use_elixir_str"))
    if "elixir_agility" in player["inventory"]:
        markup.add(types.InlineKeyboardButton("🏃 Использовать эликсир ловкости", callback_data="use_elixir_agi"))

    bot.send_message(message.chat.id, inventory_text, reply_markup=markup, parse_mode="Markdown")

def use_item(bot, call):
    player_id = call.from_user.id
    player = db.load_player(player_id)
    if player is None:
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки данных!")
        return

    item_type = call.data.split("_")[1]

    if item_type == "health_potion":
        if "health_potion" in player["inventory"]:
            player["hp"] = min(player["max_hp"], player["hp"] + 50)
            player["inventory"].remove("health_potion")
            db.save_player(player_id, player)
            bot.answer_callback_query(call.id, "💉 +50 HP!")
            show_inventory(bot, call.message)
        else:
            bot.answer_callback_query(call.id, "У тебя нет этого предмета!")

    # Обработка других предметов аналогично...

def handle_death(bot, player_id):
    player = db.load_player(player_id)
    if player is None:
        return

    # Увеличиваем счетчик смертей
    deaths = player.get("deaths", 0) + 1
    nickname = player["nickname"]

    # Создаем нового персонажа с тем же именем
    new_player = world.player_template.copy()
    new_player["nickname"] = nickname
    new_player["deaths"] = deaths

    db.save_player(player_id, new_player)

    bot.send_message(
        player_id,
        f"💀 *Ты погиб...*\n\n"
        f"Твой персонаж возрождается на первом этаже с начальными характеристиками.\n"
        f"Все твои предметы и прогресс потеряны, но имя сохранено.\n\n"
        f"Теперь ты снова *{nickname}*, но уже с опытом {deaths} смертей.",
        parse_mode="Markdown"
    )

    # Предлагаем выбрать новое оружие
    choose_weapon_after_death(bot, player_id)

def choose_weapon_after_death(bot, player_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    weapons = ["🗡️ Меч", "🔪 Кинжал", "🏏 Булава", "🏹 Лук",
               "🪓 Топор", "🔱 Копье", "🔨 Молот", "🏹 Арбалет"]
    markup.add(*weapons[:4])
    markup.add(*weapons[4:])

    bot.send_message(player_id,
                   "⚔️ *Выбери новое оружие для возрождения:*\n"
                   "🗡️ Меч - сбалансированное оружие\n"
                   "🔪 Кинжал - быстрые атаки\n"
                   "🏏 Булава - мощные удары\n"
                   "🏹 Лук - дальний бой\n"
                   "🪓 Топор - высокий урон\n"
                   "🔱 Копье - дальние атаки\n"
                   "🔨 Молот - сокрушительные удары\n"
                   "🏹 Арбалет - мощные выстрелы",
                   reply_markup=markup, parse_mode="Markdown")

    # Сохраняем состояние игрока для следующего шага
    class FakeMessage:
        def __init__(self, chat_id):
            self.chat = types.Chat(id=chat_id, type='private')
            self.from_user = types.User(id=player_id, is_bot=False, first_name='')
            self.text = ''

    bot.register_next_step_handler_by_chat_id(player_id, lambda m: set_weapon_after_death(bot, m))

def set_weapon_after_death(bot, message):
    player_id = message.from_user.id
    player = db.load_player(player_id)

    if player is None:
        bot.send_message(message.chat.id, "❌ Ошибка создания персонажа! Попробуй снова.")
        return

    weapon_choice = {
        "🗡️ Меч": "sword",
        "🔪 Кинжал": "dagger",
        "🏏 Булава": "mace",
        "🏹 Лук": "bow",
        "🪓 Топор": "axe",
        "🔱 Копье": "spear",
        "🔨 Молот": "hammer",
        "🏹 Арбалет": "crossbow"
    }

    if message.text in weapon_choice:
        weapon = weapon_choice[message.text]
        player["current_weapon"] = weapon
        player["weapons"][weapon]["level"] = 1
        player["weapons"][weapon]["skills"].append(world.weapons_data[weapon]["base_skill"])

        # Проверяем новые навыки
        check_new_skills(bot, player_id, weapon)

        db.save_player(player_id, player)

        bot.send_message(message.chat.id,
                        f"✅ Ты выбрал {world.weapons_data[weapon]['name']}!\n"
                        f"Твой первый навык: *{world.weapons_data[weapon]['base_skill']}*",
                        parse_mode="Markdown")
        show_main_menu(bot, message)
    else:
        bot.send_message(message.chat.id, "❌ Выбери оружие из списка!")
        bot.register_next_step_handler(message, lambda m: set_weapon_after_death(bot, m))