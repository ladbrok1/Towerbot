############################
### shop.py - Магазин и крафт ###
############################
"""
Модуль магазина и крафта:
- Покупка предметов
- Продажа артефактов
- Крафт предметов
- Улучшение оружия
- Система кузнеца
"""
import database as db
import world
import player
from telebot import types

def shop_menu(bot, message):
    player_id = message.from_user.id
    player_data = db.load_player(player_id)
    if player_data is None:
        bot.send_message(message.chat.id, "❌ Ошибка загрузки данных! Попробуй перезапустить бота командой /start")
        return

    shop_text = f"🛒 *Магазин Башни*\nЗолото: {player_data['gold']}\n\n*Товары:*\n"

    markup = types.InlineKeyboardMarkup()
    for item, data in world.shop_items.items():
        item_text = "{} - {}g\n{}".format(
            item.replace("_", " ").title(),
            data["price"],
            data["description"]
        )
        shop_text += item_text + "\n\n"

        markup.add(types.InlineKeyboardButton(
            f"Купить {item.replace('_', ' ')} ({data['price']}g)",
            callback_data=f"buy_{item}"
        ))

    markup.add(types.InlineKeyboardButton("Продать артефакт (100g)", callback_data="sell_artifact"))
    markup.add(types.InlineKeyboardButton("🏭 Посетить кузнеца", callback_data="blacksmith"))

    bot.send_message(message.chat.id, shop_text, reply_markup=markup, parse_mode="Markdown")

def buy_item(bot, call):
    player_id = call.from_user.id
    player_data = db.load_player(player_id)
    if player_data is None:
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки данных!")
        return

    item = call.data.split("_")[1]
    item_data = world.shop_items.get(item)

    if not item_data:
        bot.answer_callback_query(call.id, "❌ Этот предмет больше не продается!")
        return

    if player_data["gold"] >= item_data["price"]:
        player_data["gold"] -= item_data["price"]

        # Применяем эффект предмета
        effect_text = ""
        if item == "health_potion":
            player_data["inventory"].append("health_potion")
            effect_text = "💉 Зелье здоровья добавлено в инвентарь!"
        elif item == "weapon_upgrade":
            weapon = player_data["current_weapon"]
            player_data["weapons"][weapon]["level"] += 1
            effect_text = f"⚡ {world.weapons_data[weapon]['name']} улучшен до уровня {player_data['weapons'][weapon]['level']}!"
            player.check_new_skills(bot, player_id, weapon)
        elif item == "armor_upgrade":
            player_data["stats"]["defense"] += 5
            effect_text = f"🛡️ Защита увеличена до {player_data['stats']['defense']}!"
        elif item == "elixir_strength":
            player_data["inventory"].append("elixir_strength")
            effect_text = "💪 Эликсир силы добавлен в инвентарь!"
        elif item == "elixir_agility":
            player_data["inventory"].append("elixir_agility")
            effect_text = "🏃 Эликсир ловкости добавлен в инвентарь!"
        elif item == "elixir_vitality":
            player_data["inventory"].append("elixir_vitality")
            effect_text = "❤️ Эликсир живучести добавлен в инвентарь!"
        elif item == "elixir_luck":
            player_data["inventory"].append("elixir_luck")
            effect_text = "🍀 Эликсир удачи добавлен в инвентарь!"
        elif item == "boss_key":
            player_data["inventory"].append("boss_key")
            effect_text = "🔑 Ключ босса добавлен в инвентарь!"
        else:
            effect_text = "✅ Предмет куплен!"

        db.save_player(player_id, player_data)
        bot.answer_callback_query(call.id, effect_text)
        shop_menu(bot, call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота!")

def craft_item(bot, call):
    player_id = call.from_user.id
    player_data = db.load_player(player_id)
    item_id = call.data.split("_")[1]

    # Логика создания предмета
    # В реальной реализации здесь должна быть проверка материалов и создание предмета
    bot.answer_callback_query(call.id, f"🔧 Предмет {item_id} создан!")
    blacksmith_menu(bot, call.message)

def upgrade_weapon(bot, call):
    player_id = call.from_user.id
    player_data = db.load_player(player_id)
    weapon_type = call.data.split("_")[1]

    if weapon_type not in player_data["weapons"]:
        bot.answer_callback_query(call.id, "❌ У тебя нет такого оружия!")
        return

    current_level = player_data["weapons"][weapon_type]["level"]
    upgrade_cost = current_level * 500

    if player_data["gold"] >= upgrade_cost:
        player_data["gold"] -= upgrade_cost
        player_data["weapons"][weapon_type]["level"] += 1

        # Начисляем талант-пойнты каждые 5 уровней
        if player_data["weapons"][weapon_type]["level"] % 5 == 0:
            player_data["talent_points"] = player_data.get("talent_points", 0) + 1

        db.save_player(player_id, player_data)
        bot.answer_callback_query(call.id, f"⚡ Оружие улучшено до уровня {player_data['weapons'][weapon_type]['level']}!")
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота!")

    blacksmith_menu(bot, call.message)

def blacksmith_menu(bot, message):
    player_id = message.from_user.id
    player_data = db.load_player(player_id)

    if player_data is None:
        return

    markup = types.InlineKeyboardMarkup()

    # Проверяем, есть ли у игрока чертежи
    blueprints = [item for item in player_data["inventory"] if "blueprint" in item]

    if blueprints:
        for bp in blueprints:
            markup.add(types.InlineKeyboardButton(
                f"Создать {bp.replace('_', ' ')}",
                callback_data=f"craft_{bp}"
            ))

    # Кнопки улучшения оружия
    weapon = player_data["current_weapon"]
    if weapon:
        weapon_level = player_data["weapons"][weapon]["level"]
        upgrade_cost = weapon_level * 500

        markup.add(types.InlineKeyboardButton(
            f"Улучшить {world.weapons_data[weapon]['name']} (Ур. {weapon_level} → {weapon_level+1}) - {upgrade_cost}g",
            callback_data=f"upgrade_{weapon}"
        ))

    markup.add(types.InlineKeyboardButton("Расплавить предметы", callback_data="melt_items"))

    bot.send_message(
        message.chat.id,
        "🔥 *Кузница Башни*\nЗдесь можно создавать и улучшать оружие",
        reply_markup=markup,
        parse_mode="Markdown"
    )