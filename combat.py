############################
### combat.py - Боевая система ###
############################
"""
Модуль боевой системы:
- Бой с мобами
- Расчет урона
- Боевые эффекты
- Система лута
"""
import random
import math
import time
import logging
from typing import Dict, Tuple, Optional
from database import db
from player import get_player_data, save_player_data

# Настройка логирования
logger = logging.getLogger(__name__)

class CombatSystem:
    def __init__(self):
        self.mob_templates = self._load_mob_templates()
        self.boss_templates = self._load_boss_templates()
        self.combat_effects = self._load_combat_effects()

    def _load_mob_templates(self) -> Dict:
        """Загрузка шаблонов мобов из файла"""
        try:
            with open('data/mobs.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка загрузки шаблонов мобов: {e}")
            return {
                "forest_wolf": {
                    "name": "Лесной волк",
                    "hp": 50,
                    "attack": 10,
                    "defense": 5,
                    "xp": 20,
                    "gold": (5, 15),
                    "loot": ["wolf_fang", "leather"],
                    "loot_chance": 0.3
                }
            }

    def _load_boss_templates(self) -> Dict:
        """Загрузка шаблонов боссов из файла"""
        try:
            with open('data/bosses.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка загрузки шаблонов боссов: {e}")
            return {
                "ancient_dragon": {
                    "name": "Древний дракон",
                    "hp": 1000,
                    "attack": 50,
                    "defense": 30,
                    "xp": 500,
                    "gold": (200, 500),
                    "loot": ["dragon_scale", "epic_artifact"],
                    "loot_chance": 0.8
                }
            }

    def _load_combat_effects(self) -> Dict:
        """Загрузка боевых эффектов"""
        try:
            with open('data/combat_effects.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка загрузки боевых эффектов: {e}")
            return {
                "poison": {
                    "name": "Яд",
                    "duration": 3,
                    "damage_per_turn": 5,
                    "chance": 0.1
                },
                "stun": {
                    "name": "Оглушение",
                    "duration": 1,
                    "miss_turn": True,
                    "chance": 0.05
                }
            }

    def initiate_combat(self, bot, message, is_boss: bool = False) -> None:
        """Инициализация боя"""
        try:
            player_id = message.from_user.id
            player_data = get_player_data(player_id)
            
            if not player_data:
                bot.reply_to(message, "❌ Ваш персонаж не найден!")
                return
            
            if player_data.get("in_combat", False):
                bot.reply_to(message, "❌ Вы уже в бою!")
                return
            
            # Выбор моба или босса
            if is_boss:
                mob = self._select_boss(player_data.get("floor", 1))
                if not mob:
                    bot.reply_to(message, "❌ Босс не найден!")
                    return
            else:
                mob = self._select_mob(player_data.get("floor", 1))
            
            # Начало боя
            player_data["in_combat"] = True
            player_data["combat_data"] = {
                "mob": mob,
                "mob_hp": mob["hp"],
                "player_hp": player_data["stats"]["hp"],
                "effects": [],
                "turn": 0
            }
            save_player_data(player_id, player_data)
            
            # Отправка сообщения о начале боя
            self._send_combat_message(bot, message, player_data, mob, is_boss)
            
        except Exception as e:
            logger.error(f"Ошибка инициализации боя: {e}")
            bot.reply_to(message, "❌ Произошла ошибка при начале боя!")

    def _select_mob(self, floor: int) -> Dict:
        """Выбор моба в зависимости от этажа"""
        mob_pool = []
        for mob_id, mob_data in self.mob_templates.items():
            # Усиливаем мобов на высоких этажах
            scaled_mob = mob_data.copy()
            scale_factor = 1 + (floor - 1) * 0.2
            scaled_mob["hp"] = math.ceil(scaled_mob["hp"] * scale_factor)
            scaled_mob["attack"] = math.ceil(scaled_mob["attack"] * scale_factor)
            scaled_mob["defense"] = math.ceil(scaled_mob["defense"] * scale_factor)
            scaled_mob["xp"] = math.ceil(scaled_mob["xp"] * scale_factor)
            mob_pool.append(scaled_mob)
        
        return random.choice(mob_pool)

    def _select_boss(self, floor: int) -> Optional[Dict]:
        """Выбор босса в зависимости от этажа"""
        if not self.boss_templates:
            return None
        
        boss_id = random.choice(list(self.boss_templates.keys()))
        boss_data = self.boss_templates[boss_id].copy()
        
        # Усиливаем босса на высоких этажах
        scale_factor = 1 + (floor - 1) * 0.5
        boss_data["hp"] = math.ceil(boss_data["hp"] * scale_factor)
        boss_data["attack"] = math.ceil(boss_data["attack"] * scale_factor)
        boss_data["defense"] = math.ceil(boss_data["defense"] * scale_factor)
        boss_data["xp"] = math.ceil(boss_data["xp"] * scale_factor)
        
        return boss_data

    def _send_combat_message(self, bot, message, player_data: Dict, mob: Dict, is_boss: bool) -> None:
        """Отправка сообщения о бое"""
        try:
            combat_text = (
                f"⚔️ {'БОСС БИТВА! ' if is_boss else ''}Бой начался!\n\n"
                f"Вы сражаетесь с: {mob['name']}\n"
                f"❤️ HP: {mob['hp']}\n"
                f"🗡️ Атака: {mob['attack']}\n"
                f"🛡️ Защита: {mob['defense']}\n\n"
                f"Ваше здоровье: {player_data['stats']['hp']}\n\n"
                "Выберите действие:"
            )
            
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("🗡 Атаковать", callback_data="combat_attack"),
                types.InlineKeyboardButton("🛡 Защищаться", callback_data="combat_defend")
            )
            markup.row(
                types.InlineKeyboardButton("🧪 Использовать зелье", callback_data="combat_potion"),
                types.InlineKeyboardButton("🏃 Бежать", callback_data="combat_flee")
            )
            
            bot.send_message(message.chat.id, combat_text, reply_markup=markup)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о бое: {e}")
            raise

    def process_combat_action(self, bot, call, action: str) -> None:
        """Обработка боевого действия"""
        try:
            player_id = call.from_user.id
            player_data = get_player_data(player_id)
            
            if not player_data or not player_data.get("in_combat", False):
                bot.answer_callback_query(call.id, "❌ Вы не в бою!")
                return
            
            combat_data = player_data["combat_data"]
            mob = combat_data["mob"]
            
            # Обработка действия игрока
            player_damage = 0
            mob_damage = 0
            message = ""
            
            if action == "attack":
                player_damage = self._calculate_damage(
                    player_data["stats"]["attack"],
                    mob["defense"],
                    critical_chance=player_data["stats"].get("crit_chance", 0.1)
                )
                combat_data["mob_hp"] -= player_damage
                message = f"🗡 Вы атаковали и нанесли {player_damage} урона!"
            
            elif action == "defend":
                # Уменьшение получаемого урона в следующем ходу
                combat_data["defending"] = True
                message = "🛡 Вы приготовились к защите!"
            
            elif action == "potion":
                # Использование зелья (реализовать в player.py)
                message = "🧪 Вы использовали зелье лечения!"
                # Здесь должна быть логика использования зелья
            
            elif action == "flee":
                flee_chance = 0.5 + player_data["stats"].get("agility", 0) * 0.02
                if random.random() < flee_chance:
                    message = "🏃‍♂️ Вы успешно сбежали!"
                    self._end_combat(bot, call, player_id, player_data, False)
                    return
                else:
                    message = "❌ Вам не удалось сбежать!"
            
            # Проверка победы
            if combat_data["mob_hp"] <= 0:
                self._end_combat(bot, call, player_id, player_data, True)
                return
            
            # Ход моба (если игрок не защищается)
            if action != "defend":
                mob_damage = self._calculate_damage(
                    mob["attack"],
                    player_data["stats"]["defense"] * (0.5 if combat_data.get("defending", False) else 1)
                )
                combat_data["player_hp"] -= mob_damage
                message += f"\n\n{mob['name']} атаковал и нанес вам {mob_damage} урона!"
            
            # Проверка поражения
            if combat_data["player_hp"] <= 0:
                self._end_combat(bot, call, player_id, player_data, False)
                return
            
            # Сохранение состояния боя
            combat_data["turn"] += 1
            combat_data.pop("defending", None)
            save_player_data(player_id, player_data)
            
            # Отправка обновленного состояния боя
            self._update_combat_message(bot, call, player_data, mob, message)
            
        except Exception as e:
            logger.error(f"Ошибка обработки боевого действия: {e}")
            bot.answer_callback_query(call.id, "❌ Ошибка в бою!")

    def _calculate_damage(self, attack: int, defense: int, critical_chance: float = 0.0) -> int:
        """Расчет урона с учетом защиты и шанса крита"""
        base_damage = max(1, attack - defense // 2)
        if random.random() < critical_chance:
            return base_damage * 2
        return base_damage

    def _end_combat(self, bot, call, player_id: int, player_data: Dict, victory: bool) -> None:
        """Завершение боя"""
        try:
            combat_data = player_data["combat_data"]
            mob = combat_data["mob"]
            
            if victory:
                # Награда за победу
                xp_gain = mob["xp"]
                gold_gain = random.randint(*mob["gold"])
                
                player_data["stats"]["xp"] += xp_gain
                player_data["stats"]["gold"] += gold_gain
                
                # Проверка лута
                loot = []
                if random.random() < mob.get("loot_chance", 0):
                    loot_item = random.choice(mob["loot"])
                    loot.append(loot_item)
                    # Добавление предмета в инвентарь (реализовать в player.py)
                
                message = (
                    f"🎉 Победа! Вы победили {mob['name']}!\n\n"
                    f"Получено: {xp_gain} опыта и {gold_gain} золота\n"
                    f"Добыча: {', '.join(loot) if loot else 'нет'}"
                )
            else:
                # Поражение - штрафы
                gold_loss = min(player_data["stats"]["gold"], random.randint(10, 50))
                player_data["stats"]["gold"] -= gold_loss
                player_data["stats"]["hp"] = max(1, player_data["stats"]["max_hp"] // 2)
                
                message = (
                    f"☠️ Поражение! {mob['name']} победил вас.\n\n"
                    f"Вы потеряли {gold_loss} золота и восстановили половину здоровья."
                )
            
            # Выход из боя
            player_data["in_combat"] = False
            player_data.pop("combat_data", None)
            save_player_data(player_id, player_data)
            
            # Отправка сообщения о результате боя
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Ошибка завершения боя: {e}")
            bot.answer_callback_query(call.id, "❌ Ошибка при завершении боя!")

# Глобальный экземпляр боевой системы
combat_system = CombatSystem()

def initiate_combat(bot, message, is_boss: bool = False):
    combat_system.initiate_combat(bot, message, is_boss)

def handle_combat_action(bot, call):
    action = call.data.replace("combat_", "")
    combat_system.process_combat_action(bot, call, action)
