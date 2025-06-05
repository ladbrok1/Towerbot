############################
### guild.py - Система гильдий ###
############################
"""
Модуль системы гильдий:
- Создание гильдии
- Управление гильдией
- Гильдейские квесты
- Войны гильдий
- Гильдейские склады
"""
import database as db
from telebot import types

def guild_menu(bot, message):
    player_id = message.from_user.id
    player_data = db.load_player(player_id)
    
    if not player_data:
        return
    
    guild_id = player_data.get("guild_id", 0)
    guild_info = ""
    markup = types.InlineKeyboardMarkup()
    
    if guild_id > 0:
        # Игрок состоит в гильдии
        guild_data = db.get_guild(guild_id)
        guild_info = (
            f"🏰 *Твоя гильдия: {guild_data['name']}*\n"
            f"Уровень: {guild_data['level']}\n"
            f"Репутация: {guild_data['reputation']}\n"
            f"Участников: {len(json.loads(guild_data['members']))}"
        )
        
        markup.add(types.InlineKeyboardButton("👥 Информация о гильдии", callback_data="guild_info"))
        if player_id == guild_data['leader_id']:
            markup.add(types.InlineKeyboardButton("⚙️ Управление гильдией", callback_data="guild_manage"))
    else:
        # Игрок не в гильдии
        guild_info = "Ты не состоишь в гильдии."
        markup.add(types.InlineKeyboardButton("➕ Создать гильдию (5000g)", callback_data="guild_create"))
        markup.add(types.InlineKeyboardButton("🔍 Поиск гильдии", callback_data="guild_search"))
    
    bot.send_message(
        message.chat.id,
        guild_info,
        reply_markup=markup,
        parse_mode="Markdown"
    )

def handle_guild(bot, call):
    action = call.data.split("_")[1]
    
    if action == "create":
        create_guild(bot, call)
    elif action == "search":
        search_guilds(bot, call)
    # ... другие действия

def create_guild(bot, call):
    player_id = call.from_user.id
    player_data = db.load_player(player_id)
    
    if player_data["gold"] < 5000:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота!")
        return
    
    bot.send_message(call.message.chat.id, "Введи название для новой гильдии:")
    bot.register_next_step_handler(call.message, process_guild_name)

def process_guild_name(message):
    # Создание гильдии
    # ...
    pass