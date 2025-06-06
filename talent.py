import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)

class TalentType(Enum):
    """Типы талантов"""
    ATTRIBUTE = auto()      # Увеличение характеристик
    COMBAT = auto()         # Боевые умения
    CRAFTING = auto()       # Крафтовые навыки
    EXPLORATION = auto()    # Навыки исследования
    SPECIAL = auto()        # Уникальные способности

@dataclass
class TalentNode:
    """Узел дерева талантов"""
    id: str
    name: str
    description: str
    type: TalentType
    max_rank: int
    current_rank: int = 0
    requirements: List[str] = None
    cost_per_rank: List[int] = None
    effect_per_rank: List[Dict] = None

    def __post_init__(self):
        self.requirements = self.requirements or []
        self.cost_per_rank = self.cost_per_rank or [1] * self.max_rank
        self.effect_per_rank = self.effect_per_rank or [{}] * self.max_rank

    def can_unlock(self, player) -> bool:
        """Можно ли разблокировать талант"""
        if self.current_rank >= self.max_rank:
            return False
            
        for req in self.requirements:
            if not player.talents.get(req, 0) > 0:
                return False
                
        return player.talent_points >= self.cost_per_rank[self.current_rank]

    def apply_effect(self, player):
        """Применить эффект таланта"""
        if self.current_rank == 0:
            return
            
        effect = self.effect_per_rank[self.current_rank - 1]
        
        if self.type == TalentType.ATTRIBUTE:
            player.attributes[effect['attribute']] += effect['value']
        elif self.type == TalentType.COMBAT:
            player.combat_modifiers[effect['modifier']] = effect['value']
        # Другие типы эффектов...

class TalentTree:
    """Дерево талантов персонажа"""
    def __init__(self):
        self.talents: Dict[str, TalentNode] = {}
        self._initialize_talents()
    
    def _initialize_talents(self):
        """Инициализация всех доступных талантов"""
        self.talents = {
            # Базовые атрибуты
            'strength': TalentNode(
                id='strength',
                name='Сила',
                description='Увеличивает вашу атаку в ближнем бою',
                type=TalentType.ATTRIBUTE,
                max_rank=5,
                cost_per_rank=[1, 2, 3, 4, 5],
                effect_per_rank=[
                    {'attribute': 'attack', 'value': 1},
                    {'attribute': 'attack', 'value': 2},
                    {'attribute': 'attack', 'value': 3},
                    {'attribute': 'attack', 'value': 4},
                    {'attribute': 'attack', 'value': 5}
                ]
            ),
            
            # Боевые таланты
            'critical_strike': TalentNode(
                id='critical_strike',
                name='Критический удар',
                description='Шанс нанести двойной урон',
                type=TalentType.COMBAT,
                max_rank=3,
                requirements=['strength'],
                cost_per_rank=[2, 3, 4],
                effect_per_rank=[
                    {'modifier': 'crit_chance', 'value': 0.05},
                    {'modifier': 'crit_chance', 'value': 0.10},
                    {'modifier': 'crit_chance', 'value': 0.15}
                ]
            ),
            
            # Пример специального таланта
            'treasure_hunter': TalentNode(
                id='treasure_hunter',
                name='Искатель сокровищ',
                description='Увеличивает шанс найти сокровища',
                type=TalentType.EXPLORATION,
                max_rank=2,
                cost_per_rank=[3, 5],
                effect_per_rank=[
                    {'modifier': 'treasure_chance', 'value': 0.1},
                    {'modifier': 'treasure_chance', 'value': 0.2}
                ]
            )
        }
    
    def get_available_talents(self, player) -> List[TalentNode]:
        """Получить список доступных для изучения талантов"""
        return [
            talent for talent in self.talents.values() 
            if talent.can_unlock(player)
        ]
    
    def unlock_talent(self, player, talent_id: str) -> bool:
        """Попытаться изучить талант"""
        if talent_id not in self.talents:
            return False
            
        talent = self.talents[talent_id]
        
        if not talent.can_unlock(player):
            return False
            
        cost = talent.cost_per_rank[talent.current_rank]
        player.talent_points -= cost
        talent.current_rank += 1
        talent.apply_effect(player)
        
        logger.info(f"Player {player.user_id} unlocked {talent_id} rank {talent.current_rank}")
        return True

class TalentManager:
    """Менеджер талантов для игрока"""
    def __init__(self, player):
        self.player = player
        self.tree = TalentTree()
    
    def add_talent_point(self, amount: int = 1):
        """Добавить очки талантов"""
        self.player.talent_points += amount
    
    def get_talent_info(self, talent_id: str) -> Optional[TalentNode]:
        """Получить информацию о таланте"""
        return self.tree.talents.get(talent_id)
    
    def get_all_talents(self) -> Dict[str, TalentNode]:
        """Получить все таланты"""
        return self.tree.talents
    
    def unlock_talent(self, talent_id: str) -> bool:
        """Попытаться изучить талант"""
        return self.tree.unlock_talent(self.player, talent_id)
    
    def reset_talents(self, cost: int = 0) -> bool:
        """Сбросить все таланты"""
        if self.player.gold < cost:
            return False
            
        self.player.gold -= cost
        for talent in self.tree.talents.values():
            talent.current_rank = 0
        
        # Нужно пересчитать все атрибуты персонажа
        self.player.recalculate_attributes()
        return True
