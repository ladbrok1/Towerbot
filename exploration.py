import random
import logging
from typing import Dict, Tuple, Optional
from player import Player
from world import World
from combat import CombatSystem

logger = logging.getLogger(__name__)

class ExplorationSystem:
    def __init__(self, world: World, combat_system: CombatSystem):
        self.world = world
        self.combat_system = combat_system
        self.event_handlers = {
            'combat': self._handle_combat,
            'treasure': self._handle_treasure,
            'nothing': self._handle_nothing,
            'npc': self._handle_npc
        }
    
    def explore(self, player: Player, coordinates: Tuple[int, int]) -> Dict:
        """Основной метод исследования локации"""
        if not self.world.is_valid_coordinates(coordinates):
            return {"success": False, "message": "Нельзя исследовать за пределами карты"}
        
        location = self.world.get_location(coordinates)
        event = self._determine_event(player, location)
        
        result = {
            "location": location,
            "event_type": event["type"],
            "details": event["details"],
            "success": True
        }
        
        self.event_handlers[event["type"]](player, event["details"])
        
        return result
    
    def _determine_event(self, player: Player, location: Dict) -> Dict:
        """Определяет случайное событие в локации"""
        event_weights = {
            'combat': 0.4,
            'treasure': 0.2,
            'nothing': 0.3,
            'npc': 0.1
        }
        
        # Модификаторы в зависимости от типа локации
        if location.get('danger_level', 0) > 5:
            event_weights['combat'] += 0.2
            event_weights['nothing'] -= 0.1
            
        event_type = random.choices(
            list(event_weights.keys()),
            weights=list(event_weights.values()),
            k=1
        )[0]
        
        return {
            "type": event_type,
            "details": self._generate_event_details(event_type, location)
        }
    
    def _generate_event_details(self, event_type: str, location: Dict) -> Dict:
        """Генерирует детали события"""
        if event_type == 'combat':
            return {
                "enemy": self._generate_enemy(location),
                "escape_chance": 0.7
            }
        elif event_type == 'treasure':
            return {
                "gold": random.randint(5, 50),
                "items": self._generate_loot(location)
            }
        elif event_type == 'npc':
            return {
                "npc_type": random.choice(['trader', 'quest_giver', 'healer']),
                "dialogue": "Приветствую, путник!"
            }
        else:
            return {"description": "Вы ничего не нашли"}
    
    def _generate_enemy(self, location: Dict) -> Dict:
        """Создает противника на основе локации"""
        base_level = location.get('danger_level', 1)
        enemy_types = ['goblin', 'skeleton', 'bandit', 'wolf']
        
        return {
            "type": random.choice(enemy_types),
            "level": max(1, base_level + random.randint(-1, 2)),
            "health": 20 + base_level * 5,
            "attack": 5 + base_level,
            "defense": 3 + base_level,
            "reward": {
                "exp": 10 * base_level,
                "gold": random.randint(3, 15) * base_level
            }
        }
    
    def _generate_loot(self, location: Dict) -> List[Dict]:
        """Генерирует добычу"""
        loot = []
        if random.random() < 0.3:
            loot.append({
                "type": "consumable",
                "name": random.choice(["Health Potion", "Mana Potion"]),
                "effect": 20
            })
        return loot
    
    def _handle_combat(self, player: Player, details: Dict):
        """Обработчик боевого события"""
        enemy = details["enemy"]
        combat_result = self.combat_system.fight(player, enemy)
        details.update(comb
