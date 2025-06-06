############################
### main.py - Основной файл запуска ###
############################
"""
Главный модуль бота:
- Инициализация бота и БД
- Обработка команд /start и главного меню
- Координация между модулями
"""
import telebot
from telebot import types
import database as db
import player
import world
import combat
import exploration
import shop
import talent
import raid
import pvp
import economy
import guild

# Инициализация бота
TOKEN = ""
bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
db.init_db()

# Основные команды
@bot.message_handler(commands=['start'])
def start(message):
    player.handle_start(bot, message)

@bot.message_handler(func=lambda msg: msg.text == "📊 Персонаж")
def show_character(message):
    player.show_character(bot, message)

@bot.message_handler(func=lambda msg: msg.text == "📦 Инвентарь")
def show_inventory(message):
    player.show_inventory(bot, message)

@bot.message_handler(func=lambda msg: msg.text == "⚔️ Атаковать моба")
def fight_monster(message):
    combat.initiate_combat(bot, message)

@bot.message_handler(func=lambda msg: msg.text == "🏃‍♂️ Исследовать")
def explore_location(message):
    exploration.explore(bot, message)

@bot.message_handler(func=lambda msg: msg.text == "👑 Атаковать босса")
def attack_boss(message):
    raid.attack_boss(bot, message)

@bot.message_handler(func=lambda msg: msg.text == "🛒 Магазин")
def shop_menu(message):
    shop.shop_menu(bot, message)

@bot.message_handler(func=lambda msg: msg.text == "🔧 Таланты")
def show_talents(message):
    talent.show_talents(bot, message)

@bot.message_handler(func=lambda msg: msg.text == "👥 Рейды")
def raid_menu(message):
    raid.raid_menu(bot, message)

@bot.message_handler(func=lambda msg: msg.text == "⚔️ PvP")
def pvp_menu(message):
    pvp.pvp_menu(bot, message)

@bot.message_handler(func=lambda msg: msg.text == "🏦 Экономика")
def economy_menu(message):
    economy.economy_menu(bot, message)

@bot.message_handler(func=lambda msg: msg.text == "🏰 Гильдия")
def guild_menu(message):
    guild.guild_menu(bot, message)

# Обработчики callback-ов
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    try:
        if call.data.startswith("stat_"):
            player.increase_stat(bot, call)
        
        elif call.data.startswith("use_"):
            player.use_item(bot, call)
        
        elif call.data.startswith("buy_"):
            shop.buy_item(bot, call)
        
        elif call.data == "sell_artifact":
            # Обработка продажи артефакта
            player_id = call.from_user.id
            player_data = db.load_player(player_id)
            if player_data and "ancient_artifact" in player_data["inventory"]:
                player_data["inventory"].remove("ancient_artifact")
                player_data["gold"] += 100
                db.save_player(player_id, player_data)
                bot.answer_callback_query(call.id, "🏺 Ты продал артефакт за 100 золота!")
                shop.shop_menu(bot, call.message)
            else:
                bot.answer_callback_query(call.id, "❌ У тебя нет артефактов для продажи!")
        
        elif call.data == "blacksmith":
            shop.blacksmith_menu(bot, call.message)
        
        elif call.data.startswith("craft_"):
            shop.craft_item(bot, call)
        
        elif call.data.startswith("upgrade_"):
            shop.upgrade_weapon(bot, call)
        
        elif call.data == "melt_items":
            bot.answer_callback_query(call.id, "🔥 Эта функция в разработке!")
        
        elif call.data.startswith("learn_"):
            talent.learn_talent(bot, call)
        
        elif call.data == "reset_talents":
            talent.reset_talents(bot, call)
        
        elif call.data == "level_up":
            # Обработка повышения уровня
            player_id = call.from_user.id
            player_data = db.load_player(player_id)
            if player_data:
                required_exp = player_data['level'] * 100
                if player_data["exp"] >= required_exp:
                    player_data["level"] += 1
                    player_data["exp"] -= required_exp
                    player_data["stats"]["vitality"] += 1
                    player_data["max_hp"] = 80 + player_data["stats"]["vitality"] * 4
                    player_data["hp"] = player_data["max_hp"]
                    db.save_player(player_id, player_data)
                    
                    markup = types.InlineKeyboardMarkup()
                    markup.add(
                        types.InlineKeyboardButton("💪 Сила", callback_data="stat_str"),
                        types.InlineKeyboardButton("🏃 Ловкость", callback_data="stat_agi"),
                        types.InlineKeyboardButton("🎯 Точность", callback_data="stat_acc")
                    )
                    markup.add(
                        types.InlineKeyboardButton("🍀 Удача", callback_data="stat_luck"),
                        types.InlineKeyboardButton("🛡️ Защита", callback_data="stat_def"),
                        types.InlineKeyboardButton("❤️ Живучесть", callback_data="stat_vit")
                    )
                    
                    bot.send_message(call.message.chat.id, 
                                   f"🎉 Поздравляем! Ты достиг {player_data['level']}-го уровня!\n"
                                   "Выбери характеристику для улучшения:",
                                   reply_markup=markup)
                else:
                    bot.answer_callback_query(call.id, "Недостаточно опыта для повышения уровня!")
        
        elif call.data.startswith("pvp_"):
            pvp.handle_pvp(bot, call)
        
        elif call.data.startswith("raid_"):
            raid.handle_raid(bot, call)
        
        elif call.data.startswith("guild_"):
            guild.handle_guild(bot, call)
        
        elif call.data == "find_group":
            raid.find_group(bot, call)
        
        elif call.data == "create_group":
            raid.create_group(bot, call)
        
        elif call.data == "summon_epic_boss":
            raid.summon_epic_boss(bot, call)
        
        elif call.data == "economy_auction":
            bot.answer_callback_query(call.id, "🏷️ Аукцион в разработке!")
        
        elif call.data == "economy_exchange":
            bot.answer_callback_query(call.id, "💱 Биржа в разработке!")
        
        elif call.data == "economy_bank":
            bot.answer_callback_query(call.id, "🏦 Банк в разработке!")
        
        else:
            bot.answer_callback_query(call.id, "❌ Неизвестная команда!")

    except Exception as e:
        print(f"Ошибка обработки callback: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка при обработке запроса!")

if __name__ == "__main__":
    print("Бот запущен!")
    bot.polling(none_stop=True)
