############################
### exploration.py - Исследование мира ###
############################
"""
Модуль исследования мира:
- Исследование локаций
- Случайные события
- Нахождение предметов
- Секретные локации
- Встречи с другими игроками
"""
import random
import database as db
import world

def explore(bot, message):
    player_id = message.from_user.id
    player_data = db.load_player(player_id)
    
    if player_data is None:
        bot.send_message(message.chat.id, "❌ Ошибка загрузки данных! Попробуй перезапустить бота командой /start")
        return
    
    if player_data["state"] != "idle":
        bot.send_message(message.chat.id, "❌ Ты уже чем-то занят!")
        return
    
    # Проверяем, есть ли локации для исследования на этом этаже
    floor = player_data["floor"]
    if floor not in world.exploration_locations or floor > 5:
        # Для этажей выше 5 используем локации 5 этажа
        floor = min(floor, 5)
    
    # Выбираем случайную локацию
    location = random.choice(world.exploration_locations[floor])
    
    # Шанс найти что-то особенное зависит от удачи
    special_chance = player_data["stats"]["luck"] / 200
    
    # Награда за исследование
    gold_gain = random.randint(*location["gold"])
    exp_gain = location["exp"]
    
    player_data["gold"] += gold_gain
    player_data["exp"] += exp_gain
    player_data["explored"] = min(100, player_data["explored"] + random.randint(1, 5))
    
    floor_desc = world.FLOOR_DESCRIPTIONS.get(player_data["floor"], f"Этаж {player_data['floor']}")
    result_text = (
        f"🌍 На {floor_desc} ты исследуешь *{location['name']}*\n"
        f"{location['description']}\n\n"
        f"🪙 Нашел {gold_gain} золота | 🎲 Получил {exp_gain} опыта\n"
        f"🔍 Прогресс исследования: {player_data['explored']}%"
    )
    
    # Проверяем, нашли ли что-то особенное
    if "special" in location and random.random() < special_chance:
        special_item = location["special"]
        player_data["inventory"].append(special_item)
        
        if special_item == "skill_scroll":
            result_text += "\n\n📜 Ты нашел древний свиток с новым навыком!"
            # Даем случайный навык для текущего оружия
            weapon = player_data["current_weapon"]
            new_skill = get_appropriate_skill(player_data, weapon)
            if new_skill:
                player_data["weapons"][weapon]["skills"].append(new_skill)
                result_text += f"\n✨ Ты изучил *{new_skill}*!"
        # ... другие специальные предметы
    
    # Шанс встретить другого игрока (15%)
    if random.random() < 0.15:
        online_players = db.get_online_players(player_data["floor"], exclude_id=player_id)
        if online_players:
            other_player = random.choice(online_players)
            result_text += f"\n\n👥 Ты встретил игрока *{other_player['nickname']}* во время исследования!"
    
    # Шанс найти секретную локацию (5%)
    if random.random() < 0.05:
        secret_location = find_secret_location(player_data["floor"])
        result_text += f"\n\n🔍 Ты обнаружил секретную локацию: *{secret_location['name']}*!"
        # Добавляем в инвентарь ключ от локации
        player_data["inventory"].append(f"key_{secret_location['id']}")
    
    # Шанс встретить монстра (30%)
    if random.random() < 0.3:
        result_text += "\n\n⚠️ Среди руин тебя атакует монстр!"
        db.save_player(player_id, player_data)
        bot.send_message(message.chat.id, result_text, parse_mode="Markdown")
        # Инициируем бой
        # ... (код для инициации боя)
    else:
        db.save_player(player_id, player_data)
        bot.send_message(message.chat.id, result_text, parse_mode="Markdown")

def get_appropriate_skill(player_data, weapon_type):
    # ... (логика выбора навыка как в исходном коде)
    return new_skill

def find_secret_location(floor):
    secret_locations = {
        1: {"id": 101, "name": "Пещера Сокровищ", "min_level": 5},
        2: {"id": 102, "name": "Заброшенный Храм", "min_level": 10},
        # ... другие секретные локации
    }
    return random.choice(list(secret_locations.values()))