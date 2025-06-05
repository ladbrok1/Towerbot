############################
### talent.py - Система талантов ###
############################
"""
Модуль системы талантов:
- Деревья талантов для каждого оружия
- Изучение талантов
- Пассивные бонусы
- Сброс талантов
"""
import database as db
import world
from telebot import types

def show_talents(bot, message):
    player_id = message.from_user.id
    player_data = db.load_player(player_id)
    
    if not player_data or not player_data["current_weapon"]:
        bot.send_message(message.chat.id, "❌ Сначала выбери оружие!")
        return
    
    weapon = player_data["current_weapon"]
    talent_tree = world.talent_trees[weapon]
    
    talent_text = f"🌳 *Древо талантов: {world.weapons_data[weapon]['name']}*\n"
    talent_text += f"Очки талантов: {player_data.get('talent_points', 0)}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    for talent in talent_tree:
        learned = talent["id"] in player_data.get("learned_talents", [])
        talent_text += f"{'✅' if learned else '🔲'} {talent['name']} - {talent['cost']} оч."
        talent_text += f" ({talent['effect']})\n"
        
        if not learned and player_data.get('talent_points', 0) >= talent['cost']:
            markup.add(types.InlineKeyboardButton(
                f"Изучить {talent['name']}",
                callback_data=f"learn_{talent['id']}"
            ))
    
    markup.add(types.InlineKeyboardButton("🔁 Сбросить таланты (1000g)", callback_data="reset_talents"))
    
    bot.send_message(
        message.chat.id,
        talent_text,
        reply_markup=markup,
        parse_mode="Markdown"
    )

def learn_talent(bot, call):
    player_id = call.from_user.id
    player_data = db.load_player(player_id)
    talent_id = call.data.split("_")[1]
    
    if not player_data:
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки данных!")
        return
    
    # Находим талант в дереве
    weapon = player_data["current_weapon"]
    talent = next((t for t in world.talent_trees[weapon] if t["id"] == talent_id), None)
    
    if not talent:
        bot.answer_callback_query(call.id, "❌ Талант не найден!")
        return
    
    # Проверяем, можно ли изучить
    if player_data.get('talent_points', 0) >= talent['cost']:
        player_data['talent_points'] -= talent['cost']
        
        if "learned_talents" not in player_data:
            player_data["learned_talents"] = []
        player_data["learned_talents"].append(talent_id)
        
        # Применяем эффект таланта
        apply_talent_effect(player_data, talent)
        
        db.save_player(player_id, player_data)
        bot.answer_callback_query(call.id, f"✨ Ты изучил талант {talent['name']}!")
        show_talents(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно очков талантов!")

def apply_talent_effect(player_data, talent):
    # Применяем эффект таланта к персонажу
    effect = talent["effect"]
    
    if effect.startswith("damage+"):
        # Добавляем бонус к урону
        bonus = float(effect.replace("damage+", "").replace("%", "")) / 100
        # Сохраняем в активных эффектах
        player_data["active_effects"].append({
            "type": "damage_bonus",
            "value": bonus
        })
    # ... другие эффекты

def reset_talents(bot, call):
    player_id = call.from_user.id
    player_data = db.load_player(player_id)
    
    if not player_data:
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки данных!")
        return
    
    if player_data["gold"] >= 1000:
        player_data["gold"] -= 1000
        talent_points = len(player_data.get("learned_talents", []))
        player_data["talent_points"] += talent_points
        player_data["learned_talents"] = []
        
        # Удаляем эффекты талантов
        player_data["active_effects"] = [e for e in player_data["active_effects"] if e.get("source") != "talent"]
        
        db.save_player(player_id, player_data)
        bot.answer_callback_query(call.id, "🔁 Таланты сброшены!")
        show_talents(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота!")