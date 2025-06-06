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

# Константы
STAT_NAMES = {
    'strength': '💪 Сила',
    'agility': '🏃 Ловкость',
    'vitality': '❤️ Живучесть',
    'luck': '🍀 Удача',
    'accuracy': '🎯 Точность',
    'defense': '🛡️ Защита'
}

WEAPON_CHOICES = {
    "🗡️ Меч": "sword",
    "🔪 Кинжал": "dagger",
    "🏏 Булава": "mace",
    "🏹 Лук": "bow",
    "🪓 Топор": "axe",
    "🔱 Копье": "spear",
    "🔨 Молот": "hammer",
    "🏹 Арбалет": "crossbow"
}

def handle_start(bot, message):
    """Обработка команды /start"""
    player_id = message.from_user.id
    player = db.load_player(player_id)

    if not player:
        start_new_player(bot, message)
    else:
        show_main_menu(bot, message)

def start_new_player(bot, message):
    """Создание нового персонажа"""
    bot.send_message(message.chat.id, world.world_lore, parse_mode="Markdown")
    bot.send_message(message.chat.id,
                    "🌠 *Добро пожаловать в Башню Тысячи Грез!*\n"
                    "Прежде чем начать, скажи мне, как тебя зовут, искатель приключений?",
                    parse_mode="Markdown")
    bot.register_next_step_handler(message, lambda m: set_nickname(bot, m))

def set_nickname(bot, message):
    """Установка имени персонажа"""
    player_id = message.from_user.id
    nickname = message.text.strip()
    
    if not nickname or len(nickname) > 20:
        bot.send_message(message.chat.id, "❌ Имя должно быть от 1 до 20 символов!")
        bot.register_next_step_handler(message, lambda m: set_nickname(bot, m))
        return

    player = world.player_template.copy()
    player["nickname"] = nickname
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
    bot.register_next_step_handler(message, lambda m: set_stats(bot, m))

def set_stats(bot, message):
    """Установка характеристик персонажа"""
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
            db.save_player(player_id, player)
            
            show_weapon_selection(bot, message)
        else:
            raise ValueError
    except:
        bot.send_message(message.chat.id, "❌ Ошибка! Введи 6 чисел (сумма=25).")
        bot.register_next_step_handler(message, lambda m: set_stats(bot, m))

def show_weapon_selection(bot, message):
    """Показ меню выбора оружия"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    weapons = list(WEAPON_CHOICES.keys())
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
    bot.register_next_step_handler(message, lambda m: set_weapon(bot, m))

def set_weapon(bot, message, after_death=False):
    """Установка оружия персонажа"""
    player_id = message.from_user.id
    player = db.load_player(player_id)

    if player is None:
        bot.send_message(message.chat.id, "❌ Ошибка создания персонажа! Попробуй снова.")
        return

    if message.text in WEAPON_CHOICES:
        weapon = WEAPON_CHOICES[message.text]
        
        if weapon not in world.weapons_data:
            bot.send_message(message.chat.id, f"❌ Ошибка конфигурации: оружие {weapon} не найдено!")
            return

        player["current_weapon"] = weapon
        player["weapons"][weapon] = {"level": 1, "skills": [world.weapons_data[weapon]["base_skill"]]}
        db.save_player(player_id, player)

        check_new_skills(bot, player_id, weapon)
        
        response = (f"✅ Ты {'возродился с' if after_death else 'выбрал'} " 
                   f"{world.weapons_data[weapon]['name']}!\n"
                   f"Твой первый навык: *{world.weapons_data[weapon]['base_skill']}*")
        
        bot.send_message(message.chat.id, response, parse_mode="Markdown")
        show_main_menu(bot, message)
    else:
        bot.send_message(message.chat.id, "❌ Выбери оружие из списка!")
        bot.register_next_step_handler(message, lambda m: set_weapon(bot, m, after_death))

def check_new_skills(bot, player_id, weapon_type):
    """Проверка доступных для изучения навыков"""
    player = db.load_player(player_id)
    if player is None:
        return

    weapon_data = world.weapons_data.get(weapon_type, {})
    if not weapon_data:
        return

    stats = player["stats"]
    weapon_level = player["weapons"].get(weapon_type, {}).get("level", 1)
    current_skills = player["weapons"].get(weapon_type, {}).get("skills", [])

    # Определяем доминирующую характеристику
    dominant_stat = max(stats, key=stats.get)
    stat_value = stats[dominant_stat]

    # Выбираем подходящие навыки
    available_skills = []
    for skill_name, skill_data in weapon_data.get("skills", {}).items():
        # Проверяем требования для навыка
        req_met = True
        for stat, value in skill_data.items():
            if stat.startswith("min_"):
                stat_name = stat[4:]
                if stats.get(stat_name, 0) < value:
                    req_met = False
                    break

        # Если требования выполнены и навык еще не получен
        if req_met and skill_name not in current_skills:
            # Предпочтение навыкам, соответствующим доминирующей характеристике
            if weapon_data.get("stat") == dominant_stat:
                available_skills.insert(0, skill_name)
            else:
                available_skills.append(skill_name)

    # Если есть доступные навыки, выбираем случайный
    if available_skills:
        new_skill = random.choice(available_skills)
        player["weapons"][weapon_type]["skills"].append(new_skill)
        db.save_player(player_id, player)
        
        bot.send_message(player_id,
                       f"✨ Ты освоил новый навык: *{new_skill}*!\n"
                       f"Используй его в бою с помощью кнопки навыков.",
                       parse_mode="Markdown")

def show_main_menu(bot, message):
    """Отображение главного меню игрока"""
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
    if weapon and weapon in world.weapons_data:
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
    """Отображение информации о персонаже"""
    player_id = message.from_user.id
    player = db.load_player(player_id)
    if not player:
        bot.send_message(message.chat.id, "❌ Ошибка загрузки данных!")
        return

    weapon = player["current_weapon"]
    weapon_data = world.weapons_data.get(weapon, {})
    weapon_name = weapon_data.get("name", "Не выбрано")
    weapon_level = player["weapons"].get(weapon, {}).get("level", 0)
    weapon_skills = ", ".join(player["weapons"].get(weapon, {}).get("skills", []))

    stats_text = "\n".join(
        f"{STAT_NAMES.get(stat, '❓')}: {value}"
        for stat, value in player["stats"].items()
    )

    required_exp = player['level'] * 100
    character_info = (
        f"👤 *{player['nickname']}*\n"
        f"🏆 Уровень: {player['level']} ({player['exp']}/{required_exp} опыта)\n"
        f"🏠 Этаж: {player['floor']}\n"
        f"💀 Смертей: {player.get('deaths', 0)}\n\n"
        f"⚔️ *Оружие:* {weapon_name} (Ур. {weapon_level})\n"
        f"🔮 Навыки: {weapon_skills or 'Нет навыков'}\n\n"
        f"📊 *Характеристики:*\n{stats_text}"
    )

    markup = types.InlineKeyboardMarkup()
    if player["exp"] >= required_exp:
        markup.add(types.InlineKeyboardButton("⬆️ Повысить уровень", callback_data="level_up"))

    bot.send_message(message.chat.id, character_info, reply_markup=markup, parse_mode="Markdown")

def increase_stat(bot, call):
    """Повышение характеристики при уровне"""
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

    stat = stat_map.get(call.data)
    if not stat:
        bot.answer_callback_query(call.id, "❌ Неверный выбор характеристики!")
        return

    player["stats"][stat] += 1

    # Обновляем производные характеристики
    if stat == "vitality":
        player["max_hp"] = 80 + player["stats"]["vitality"] * 4
        player["hp"] = min(player["hp"], player["max_hp"])

    db.save_player(player_id, player)
    bot.answer_callback_query(call.id, f"{STAT_NAMES[stat]} увеличена!")
    show_character(bot, call.message)

def show_inventory(bot, message):
    """Отображение инвентаря игрока"""
    player_id = message.from_user.id
    player = db.load_player(player_id)
    if not player:
        bot.send_message(message.chat.id, "❌ Ошибка загрузки данных!")
        return

    inventory = player.get("inventory", {})
    if not inventory:
        bot.send_message(message.chat.id, "🎒 *Твой инвентарь пуст!*", parse_mode="Markdown")
        return

    inventory_text = "🎒 *Твой инвентарь:*\n"
    for item, quantity in inventory.items():
        item_name = world.ITEMS.get(item, {}).get("name", item)
        inventory_text += f"- {item_name}: {quantity} шт.\n"

    markup = types.InlineKeyboardMarkup()
    if "health_potion" in inventory:
        markup.add(types.InlineKeyboardButton("💉 Использовать зелье здоровья", callback_data="use_health_potion"))
    if "elixir_strength" in inventory:
        markup.add(types.InlineKeyboardButton("💪 Использовать эликсир силы", callback_data="use_elixir_str"))
    if "elixir_agility" in inventory:
        markup.add(types.InlineKeyboardButton("🏃 Использовать эликсир ловкости", callback_data="use_elixir_agi"))

    bot.send_message(message.chat.id, inventory_text, reply_markup=markup, parse_mode="Markdown")

def use_item(bot, call):
    """Использование предмета из инвентаря"""
    player_id = call.from_user.id
    player = db.load_player(player_id)
    if not player:
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки данных!")
        return

    item_type = call.data.split("_")[1]
    inventory = player.get("inventory", {})

    item_effects = {
        "health_potion": {
            "effect": lambda p: p.update({"hp": min(p["max_hp"], p["hp"] + 50)}),
            "message": "💉 +50 HP!",
            "success": "health_potion" in inventory
        },
        "elixir_str": {
            "effect": lambda p: p["stats"].update({"strength": p["stats"]["strength"] + 5}),
            "message": "💪 +5 к силе на 1 час!",
            "success": "elixir_strength" in inventory
        },
        "elixir_agi": {
            "effect": lambda p: p["stats"].update({"agility": p["stats"]["agility"] + 5}),
            "message": "🏃 +5 к ловкости на 1 час!",
            "success": "elixir_agility" in inventory
        }
    }

    effect = item_effects.get(item_type)
    if not effect or not effect["success"]:
        bot.answer_callback_query(call.id, "❌ У тебя нет этого предмета!")
        return

    # Применяем эффект предмета
    effect["effect"](player)
    
    # Удаляем предмет из инвентаря
    item_key = {
        "health_potion": "health_potion",
        "elixir_str": "elixir_strength",
        "elixir_agi": "elixir_agility"
    }[item_type]
    
    player["inventory"][item_key] -= 1
    if player["inventory"][item_key] <= 0:
        del player["inventory"][item_key]

    db.save_player(player_id, player)
    bot.answer_callback_query(call.id, effect["message"])
    show_inventory(bot, call.message)

def handle_death(bot, player_id):
    """Обработка смерти персонажа"""
    player = db.load_player(player_id)
    if not player:
        return

    # Увеличиваем счетчик смертей
    deaths = player.get("deaths", 0) + 1
    nickname = player["nickname"]

    # Создаем нового персонажа с тем же именем
    new_player = world.player_template.copy()
    new_player["nickname"] = nickname
    new_player["deaths"] = deaths
    new_player["floor"] = 1  # Начинаем с первого этажа

    db.save_player(player_id, new_player)

    bot.send_message(
        player_id,
        f"💀 *Ты погиб...*\n\n"
        f"Твой персонаж возрождается на первом этаже с начальными характеристиками.\n"
        f"Все твои предметы и прогресс потеряны, но имя сохранено.\n\n"
        f"Теперь ты снова *{nickname}*, но уже с опытом {deaths} смертей.",
        parse_mode="Markdown"
    )

    # Выдаем достижение
    check_achievements(bot, player_id, "first_death")
    
    # Предлагаем выбрать новое оружие
    choose_weapon_after_death(bot, player_id)

def choose_weapon_after_death(bot, player_id):
    """Выбор оружия после смерти"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    weapons = list(WEAPON_CHOICES.keys())
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

    # Создаем fake message для обработки
    class FakeMessage:
        def __init__(self, chat_id, user_id):
            self.chat = types.Chat(id=chat_id, type='private')
            self.from_user = types.User(id=user_id, is_bot=False, first_name='')
            self.text = ''

    fake_msg = FakeMessage(player_id, player_id)
    bot.register_next_step_handler(fake_msg, lambda m: set_weapon(bot, m, after_death=True))

def check_achievements(bot, player_id, achievement_type):
    """Проверка и выдача достижений"""
    player = db.load_player(player_id)
    if not player:
        return

    achievements = player.get("achievements", {})
    
    if achievement_type == "first_death" and not achievements.get("first_death"):
        achievements["first_death"] = True
        player["achievements"] = achievements
        db.save_player(player_id, player)
        bot.send_message(player_id, "🏆 Получено достижение: *Первая кровь*!", parse_mode="Markdown")
        
def add_item_to_inventory(bot, player_id, item_name, amount=1):
    """Добавление предмета в инвентарь"""
    player = db.load_player(player_id)
    if not player:
        return False

    if "inventory" not in player:
        player["inventory"] = {}

    if item_name in player["inventory"]:
        player["inventory"][item_name] += amount
    else:
        player["inventory"][item_name] = amount

    db.save_player(player_id, player)
    return True
    
def calculate_secondary_stats(player):
    """Расчет производных характеристик"""
    stats = player["stats"]
    player["max_hp"] = 80 + stats["vitality"] * 4
    player["crit_chance"] = min(0.3, stats["strength"] * 0.01 + stats["luck"] * 0.005)
    player["dodge_chance"] = min(0.4, stats["agility"] * 0.015)
    player["armor"] = stats["defense"] * 2
    
