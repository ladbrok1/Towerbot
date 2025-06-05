############################
### combat.py - Боевая система (PvE) ###
############################
"""
Модуль боевой системы:
- Бой с монстрами
- Бой с боссами
- Механики навыков
- Расчет урона
- Смерть игрока
"""
import random
import database as db
import player
import world

def initiate_combat(bot, message):
    player_id = message.from_user.id
    player_data = db.load_player(player_id)
    
    if player_data is None:
        bot.send_message(message.chat.id, "❌ Ошибка загрузки данных! Попробуй перезапустить бота командой /start")
        return
    
    if player_data["state"] != "idle":
        bot.send_message(message.chat.id, "❌ Ты уже в бою!")
        return
    
    player_data["state"] = "fighting"
    
    # Выбираем монстра в зависимости от этажа
    floor = player_data["floor"]
    if floor > 10:
        floor = 10  # Максимальный этаж с мобами
    
    floor_monsters = world.monsters_data.get(floor, world.monsters_data[1])
    monster = random.choice(floor_monsters).copy()
    
    # Шанс встретить другого игрока (15%)
    if random.random() < 0.15:
        online_players = db.get_online_players(player_data["floor"], exclude_id=player_id)
        if online_players:
            other_player = random.choice(online_players)
            bot.send_message(
                player_id, 
                f"👥 Ты встретил игрока *{other_player['nickname']}* во время боя!\n"
                "Он присоединяется к тебе против монстра!",
                parse_mode="Markdown"
            )
            # Увеличиваем награду за бой
            monster["gold"] = (monster["gold"][0] * 2, monster["gold"][1] * 2)
            monster["exp"] *= 1.5
    
    # Сохраняем монстра в состоянии игрока
    player_data["current_enemy"] = monster
    db.save_player(player_id, player_data)
    
    # Создаем клавиатуру для боя
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    weapon = player_data["current_weapon"]
    skills = player_data["weapons"][weapon]["skills"]
    
    markup.add(f"⚔️ Атаковать ({world.weapons_data[weapon]['base_skill']})")
    for skill in skills[1:]:  # Первый навык - базовый
        markup.add(f"🔮 {skill}")
    
    if "health_potion" in player_data["inventory"]:
        markup.add("💉 Зелье здоровья")
    
    markup.add("🏃 Бежать")
    
    floor_desc = world.FLOOR_DESCRIPTIONS.get(player_data["floor"], f"Этаж {player_data['floor']}")
    bot.send_message(
        message.chat.id,
        f"⚔️ На {floor_desc} ты встретил *{monster['name']}*!\n"
        f"❤️ HP: {monster['hp']} | 💢 Урон: {monster['damage']}\n\n"
        "Выбери действие:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

def calculate_damage(player_data, skill_name=None):
    # ... (логика расчета урона как в исходном коде)
    return damage, effect_text

def handle_attack(bot, player_id, skill_name=None):
    # ... (логика обработки атаки как в исходном коде)
    return battle_text, player_state, battle_ended

# Остальные функции боя аналогично исходному коду...