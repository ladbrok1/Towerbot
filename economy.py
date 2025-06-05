############################
### economy.py - Экономическая система ###
############################
"""
Модуль экономической системы:
- Аукцион
- Игровая биржа
- Банковская система
- Налоги и сборы
- Игровая валюта
"""
from telebot import types

def economy_menu(bot, message):
    player_id = message.from_user.id
    player_data = db.load_player(player_id)
    
    if not player_data:
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏷️ Аукцион", callback_data="economy_auction"))
    markup.add(types.InlineKeyboardButton("💱 Биржа ресурсов", callback_data="economy_exchange"))
    markup.add(types.InlineKeyboardButton("🏦 Банк", callback_data="economy_bank"))
    
    economy_info = (
        f"🏦 *Экономическая система*\n"
        f"🪙 Золото: {player_data['gold']}\n"
        f"💎 Кристаллы: {player_data.get('crystals', 0)}\n\n"
        f"Выбери действие:"
    )
    
    bot.send_message(
        message.chat.id,
        economy_info,
        reply_markup=markup,
        parse_mode="Markdown"
    )