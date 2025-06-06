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
import leveling
import quest
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота
try:
    TOKEN = "7698580548:AAGxtJRhkJBDhffYqUhJ_FtHpyMqlHEt1AA"
    bot = telebot.TeleBot(TOKEN, parse_mode='HTML')
    logger.info("Бот успешно инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации бота: {e}")
    raise

# Инициализация базы данных
try:
    db.init_db()
    logger.info("База данных успешно инициализирована")
except Exception as e:
    logger.error(f"Ошибка инициализации БД: {e}")
    raise

# Основные команды
@bot.message_handler(commands=['start', 'help'])
def start(message):
    try:
        player.handle_start(bot, message)
    except Exception as e:
        logger.error(f"Ошибка в команде /start: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при обработке команды")

@bot.message_handler(func=lambda msg: msg.text == "📊 Персонаж")
def show_character(message):
    try:
        player.show_character(bot, message)
    except Exception as e:
        logger.error(f"Ошибка показа персонажа: {e}")
        bot.reply_to(message, "❌ Не удалось загрузить данные персонажа")

# Остальные обработчики сообщений (для краткости оставлены без изменений, но должны иметь аналогичную обработку ошибок)
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

@bot.message_handler(func=lambda msg: msg.text == "📜 Квесты")
def quests_menu(message):
    quest.show_quests(bot, message)

# Обработчики callback-ов (добавлена обработка ошибок)
def handle_callback_action(call, handler_func, success_msg=None):
    try:
        handler_func(bot, call)
        if success_msg:
            bot.answer_callback_query(call.id, success_msg)
    except Exception as e:
        logger.error(f"Ошибка обработки callback {call.data}: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка при обработке запроса")

def handle_stat_call(call):
    handle_callback_action(call, player.increase_stat, "📈 Характеристика увеличена!")

def handle_use_item(call):
    handle_callback_action(call, player.use_item, "🎯 Предмет использован!")

def handle_buy_item(call):
    handle_callback_action(call, shop.buy_item)

def handle_sell_artifact(call):
    handle_callback_action(call, player.sell_artifact, "💰 Артефакт продан!")
    shop.shop_menu(bot, call.message)

def handle_blacksmith(call):
    handle_callback_action(call, shop.blacksmith_menu)

def handle_craft_item(call):
    handle_callback_action(call, shop.craft_item, "🔨 Предмет создан!")

def handle_upgrade_weapon(call):
    handle_callback_action(call, shop.upgrade_weapon, "⚡ Оружие улучшено!")

def handle_learn_talent(call):
    handle_callback_action(call, talent.learn_talent, "🧠 Талант изучен!")

def handle_reset_talents(call):
    handle_callback_action(call, talent.reset_talents, "🔄 Таланты сброшены!")

def handle_level_up(call):
    handle_callback_action(call, leveling.handle_level_up)

def handle_pvp(call):
    handle_callback_action(call, pvp.handle_pvp)

def handle_raid(call):
    handle_callback_action(call, raid.handle_raid)

def handle_guild(call):
    handle_callback_action(call, guild.handle_guild)

def handle_find_group(call):
    handle_callback_action(call, raid.find_group)

def handle_create_group(call):
    handle_callback_action(call, raid.create_group)

def handle_summon_boss(call):
    handle_callback_action(call, raid.summon_epic_boss)

def handle_quest(call):
    handle_callback_action(call, quest.handle_quest_action)

# Главный обработчик callback-ов
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    try:
        callback_actions = {
            "stat_": handle_stat_call,
            "use_": handle_use_item,
            "buy_": handle_buy_item,
            "sell_artifact": handle_sell_artifact,
            "blacksmith": handle_blacksmith,
            "craft_": handle_craft_item,
            "upgrade_": handle_upgrade_weapon,
            "learn_": handle_learn_talent,
            "reset_talents": handle_reset_talents,
            "level_up": handle_level_up,
            "pvp_": handle_pvp,
            "raid_": handle_raid,
            "guild_": handle_guild,
            "find_group": handle_find_group,
            "create_group": handle_create_group,
            "summon_epic_boss": handle_summon_boss,
            "quest_": handle_quest,
            "economy_auction": lambda c: bot.answer_callback_query(c.id, "🏷️ Аукцион в разработке!"),
            "economy_exchange": lambda c: bot.answer_callback_query(c.id, "💱 Биржа в разработке!"),
            "economy_bank": lambda c: bot.answer_callback_query(c.id, "🏦 Банк в разработке!"),
            "melt_items": lambda c: bot.answer_callback_query(c.id, "🔥 Плавка предметов в разработке!")
        }
        
        for prefix, action in callback_actions.items():
            if call.data.startswith(prefix) or call.data == prefix:
                action(call)
                return
        
        bot.answer_callback_query(call.id, "❌ Неизвестная команда!")

    except Exception as e:
        logger.error(f"Необработанная ошибка в callback: {e}")
        bot.answer_callback_query(call.id, "❌ Критическая ошибка при обработке запроса!")

if __name__ == "__main__":
    logger.info("Бот запущен!")
    try:
        bot.polling(none_stop=True, interval=1, timeout=30)
    except Exception as e:
        logger.error(f"Ошибка в работе бота: {e}")
