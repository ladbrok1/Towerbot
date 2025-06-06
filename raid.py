import logging
import random
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime, timedelta
from database import Database
from player import Player
from combat import CombatSystem
from world import World

logger = logging.getLogger(__name__)

class RaidDifficulty(Enum):
    NORMAL = auto()
    HEROIC = auto()
    MYTHIC = auto()

class RaidStatus(Enum):
    RECRUITING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass
class RaidBoss:
    id: str
    name: str
    health: int
    abilities: List[Dict]
    enrage_timer: int  # в секундах
    loot_table: Dict[str, float]

@dataclass
class RaidMember:
    player: Player
    role: str  # "tank", "healer", "dps"
    ready: bool = False

@dataclass
class Raid:
    raid_id: str
    boss: RaidBoss
    difficulty: RaidDifficulty
    status: RaidStatus
    members: List[RaidMember]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_boss_health: Optional[int] = None

class RaidManager:
    def __init__(self, db: Database, combat_system: CombatSystem, world: World):
        self.db = db
        self.combat_system = combat_system
        self.world = world
        self.active_raids: Dict[str, Raid] = {}
        self.raid_queue: List[Tuple[Player, str]] = []  # (player, role)
        self.bosses: Dict[str, RaidBoss] = self._load_bosses()
        self._initialize_db()

    def _initialize_db(self):
        """Создать необходимые таблицы в БД"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raid_history (
                    raid_id TEXT PRIMARY KEY,
                    boss_id TEXT,
                    difficulty TEXT,
                    status TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    members TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS raid_loot (
                    raid_id TEXT,
                    player_id INTEGER,
                    item_id TEXT,
                    timestamp TEXT,
                    PRIMARY KEY (raid_id, player_id, item_id)
                )
            """)
            conn.commit()

    def _load_bosses(self) -> Dict[str, RaidBoss]:
        """Загрузить боссов для рейдов из конфига"""
        return {
            "ancient_dragon": RaidBoss(
                id="ancient_dragon",
                name="Древний Дракон",
                health=500000,
                abilities=[
                    {
                        "name": "Огненное дыхание",
                        "damage": 1500,
                        "cooldown": 30,
                        "aoe": True
                    },
                    {
                        "name": "Удар хвостом",
                        "damage": 800,
                        "cooldown": 20,
                        "stun_chance": 0.3
                    }
                ],
                enrage_timer=600,
                loot_table={
                    "dragon_scale": 0.7,
                    "flame_sword": 0.2,
                    "dragon_heart": 0.1
                }
            )
        }

    async def create_raid(self, leader: Player, boss_id: str, difficulty: RaidDifficulty) -> Optional[Raid]:
        """Создать новый рейд"""
        if boss_id not in self.bosses:
            return None

        raid_id = f"raid_{leader.user_id}_{int(datetime.now().timestamp())}"
        new_raid = Raid(
            raid_id=raid_id,
            boss=self.bosses[boss_id],
            difficulty=difficulty,
            status=RaidStatus.RECRUITING,
            members=[RaidMember(player=leader, role="dps")],
            current_boss_health=self._get_scaled_boss_health(boss_id, difficulty)
        )

        self.active_raids[raid_id] = new_raid
        return new_raid

    def _get_scaled_boss_health(self, boss_id: str, difficulty: RaidDifficulty) -> int:
        """Получить здоровье босса с учетом сложности"""
        base_health = self.bosses[boss_id].health
        if difficulty == RaidDifficulty.HEROIC:
            return int(base_health * 1.5)
        elif difficulty == RaidDifficulty.MYTHIC:
            return int(base_health * 2.0)
        return base_health

    async def join_raid(self, raid_id: str, player: Player, role: str) -> bool:
        """Присоединиться к рейду"""
        if raid_id not in self.active_raids:
            return False

        raid = self.active_raids[raid_id]

        # Проверка дублирования игрока
        if any(m.player.user_id == player.user_id for m in raid.members):
            return False

        # Проверка ролей (можно расширить)
        if role not in ["tank", "healer", "dps"]:
            return False

        raid.members.append(RaidMember(player=player, role=role))
        return True

    async def leave_raid(self, raid_id: str, player: Player) -> bool:
        """Покинуть рейд"""
        if raid_id not in self.active_raids:
            return False

        raid = self.active_raids[raid_id]
        raid.members = [m for m in raid.members if m.player.user_id != player.user_id]

        # Если рейд пуст - удалить
        if not raid.members:
            del self.active_raids[raid_id]

        return True

    async def start_raid(self, raid_id: str) -> bool:
        """Начать рейд"""
        if raid_id not in self.active_raids:
            return False

        raid = self.active_raids[raid_id]

        # Минимальные требования для старта
        if len([m for m in raid.members if m.role == "tank"]) < 2:
            return False
        if len([m for m in raid.members if m.role == "healer"]) < 3:
            return False
        if len(raid.members) < 10:
            return False

        raid.status = RaidStatus.IN_PROGRESS
        raid.start_time = datetime.now()
        return True

    async def _raid_tick(self, raid: Raid):
        """Обработка одного тика рейда (вызывается периодически)"""
        if raid.status != RaidStatus.IN_PROGRESS:
            return

        # Проверка таймера энрейдж
        elapsed = (datetime.now() - raid.start_time).total_seconds()
        if elapsed > raid.boss.enrage_timer:
            await self._end_raid(raid.raid_id, success=False)
            return

        # Обработка способностей босса
        for ability in raid.boss.abilities:
            # Упрощенная логика использования способностей
            if random.random() < 0.1:  # 10% шанс использовать способность
                await self._use_boss_ability(raid, ability)

        # Проверка победы
        if raid.current_boss_health <= 0:
            await self._end_raid(raid.raid_id, success=True)

    async def _use_boss_ability(self, raid: Raid, ability: Dict):
        """Обработка способности босса"""
        # Логика урона по игрокам
        for member in raid.members:
            damage = ability["damage"]
            
            # Модификаторы для танков
            if member.role == "tank":
                damage *= 0.6
            
            # Применение урона
            member.player.take_damage(int(damage))
            
            # Дополнительные эффекты
            if ability.get("stun_chance", 0) > random.random():
                member.player.apply_effect("stun", duration=2)

    async def _end_raid(self, raid_id: str, success: bool):
        """Завершить рейд"""
        if raid_id not in self.active_raids:
            return

        raid = self.active_raids[raid_id]
        raid.status = RaidStatus.COMPLETED if success else RaidStatus.FAILED
        raid.end_time = datetime.now()

        # Награждение игроков
        if success:
            await self._distribute_loot(raid)

        # Сохранение в историю
        await self._save_raid_history(raid)

        # Очистка
        del self.active_raids[raid_id]

    async def _distribute_loot(self, raid: Raid):
        """Распределить добычу после успешного рейда"""
        loot_winners = {}
        
        for item_id, drop_chance in raid.boss.loot_table.items():
            if random.random() < drop_chance:
                # Упрощенная система распределения лута
                eligible_players = [m.player for m in raid.members]
                winner = random.choice(eligible_players)
                
                if winner.user_id not in loot_winners:
                    loot_winners[winner.user_id] = []
                loot_winners[winner.user_id].append(item_id)
                
                winner.add_to_inventory(item_id)

        # Сохранение информации о луте
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for player_id, items in loot_winners.items():
                for item_id in items:
                    cursor.execute("""
                        INSERT INTO raid_loot 
                        (raid_id, player_id, item_id, timestamp) 
                        VALUES (?, ?, ?, ?)
                    """, (
                        raid.raid_id,
                        player_id,
                        item_id,
                        datetime.now().isoformat()
                    ))
            conn.commit()

    async def _save_raid_history(self, raid: Raid):
        """Сохранить информацию о рейде в БД"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO raid_history 
                (raid_id, boss_id, difficulty, status, start_time, end_time, members) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                raid.raid_id,
                raid.boss.id,
                raid.difficulty.name,
                raid.status.name,
                raid.start_time.isoformat() if raid.start_time else None,
                raid.end_time.isoformat() if raid.end_time else None,
                json.dumps([m.player.user_id for m in raid.members])
            ))
            conn.commit()

    async def get_player_raid(self, player_id: int) -> Optional[Raid]:
        """Получить рейд, в котором состоит игрок"""
        for raid in self.active_raids.values():
            if any(m.player.user_id == player_id for m in raid.members):
                return raid
        return None

    async def find_raid(self, boss_id: str, difficulty: RaidDifficulty) -> Optional[Raid]:
        """Найти подходящий рейд для присоединения"""
        for raid in self.active_raids.values():
            if (raid.boss.id == boss_id and 
                raid.difficulty == difficulty and 
                raid.status == RaidStatus.RECRUITING and
                len(raid.members) < 25):  # Максимальный размер рейда
                return raid
        return None

    async def queue_for_raid(self, player: Player, role: str) -> bool:
        """Встать в очередь на поиск рейда"""
        self.raid_queue.append((player, role))
        return True

    async def process_raid_queue(self):
        """Обработать очередь и создать рейды"""
        # Группировка по ролям
        tanks = [p for p, r in self.raid_queue if r == "tank"]
        healers = [p for p, r in self.raid_queue if r == "healer"]
        dps = [p for p, r in self.raid_queue if r == "dps"]

        # Проверка минимальных требований
        if len(tanks) >= 2 and len(healers) >= 3 and len(dps) >= 5:
            # Создать новый рейд
            leader = dps[0]  # Первый DPS становится лидером
            raid = await self.create_raid(leader, "ancient_dragon", RaidDifficulty.NORMAL)
            
            # Добавить участников
            for tank in tanks[:2]:
                await self.join_raid(raid.raid_id, tank, "tank")
            
            for healer in healers[:3]:
                await self.join_raid(raid.raid_id, healer, "healer")
            
            for dps_player in dps[:10]:  # Ограничение на 10 DPS
                await self.join_raid(raid.raid_id, dps_player, "dps")
            
            # Удалить добавленных игроков из очереди
            self.raid_queue = [p for p in self.raid_queue if p[0] not in [tank for tank in tanks[:2]] and
                                                           p[0] not in [healer for healer in healers[:3]] and
                                                           p[0] not in [dps_p for dps_p in dps[:10]]]
            
            return raid
        return None

    async def get_raid_status(self, raid_id: str) -> Dict:
        """Получить статус рейда"""
        if raid_id not in self.active_raids:
            return {"error": "Raid not found"}
        
        raid = self.active_raids[raid_id]
        return {
            "boss": raid.boss.name,
            "difficulty": raid.difficulty.name,
            "status": raid.status.name,
            "health_percent": (raid.current_boss_health / self._get_scaled_boss_health(raid.boss.id, raid.difficulty)) * 100,
            "members": [{
                "name": m.player.name,
                "role": m.role,
                "ready": m.ready
            } for m in raid.members],
            "time_elapsed": (datetime.now() - raid.start_time).total_seconds() if raid.start_time else 0
        }
