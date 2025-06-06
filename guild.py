import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum, auto
from database import Database

logger = logging.getLogger(__name__)

class GuildRank(Enum):
    RECRUIT = auto()
    MEMBER = auto()
    OFFICER = auto()
    LEADER = auto()

@dataclass
class GuildMember:
    user_id: int
    rank: GuildRank
    joined_at: datetime
    contribution: int
    last_online: datetime

@dataclass
class GuildBankItem:
    item_id: str
    quantity: int
    deposited_by: int
    deposited_at: datetime

class Guild:
    def __init__(self, db: Database, guild_id: int):
        self.db = db
        self.guild_id = guild_id
        self.name: str = ""
        self.tag: str = ""
        self.level: int = 1
        self.exp: int = 0
        self.members: Dict[int, GuildMember] = {}
        self.bank: Dict[str, GuildBankItem] = {}
        self.bank_balance: int = 0
        self.created_at: datetime = datetime.now()
        self.motd: str = ""
        self.load_guild_data()

    def load_guild_data(self):
        """Загрузить данные гильдии из БД"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Основная информация о гильдии
            cursor.execute("SELECT name, tag, level, exp, created_at, motd FROM guilds WHERE id = ?", (self.guild_id,))
            guild_data = cursor.fetchone()
            
            if not guild_data:
                raise ValueError(f"Guild with ID {self.guild_id} not found")
                
            self.name, self.tag, self.level, self.exp, self.created_at, self.motd = guild_data
            
            # Участники гильдии
            cursor.execute("""
                SELECT user_id, rank, joined_at, contribution, last_online 
                FROM guild_members 
                WHERE guild_id = ?
            """, (self.guild_id,))
            
            for row in cursor.fetchall():
                self.members[row[0]] = GuildMember(
                    user_id=row[0],
                    rank=GuildRank(row[1]),
                    joined_at=datetime.fromisoformat(row[2]),
                    contribution=row[3],
                    last_online=datetime.fromisoformat(row[4])
                )
            
            # Банк гильдии
            cursor.execute("""
                SELECT item_id, quantity, deposited_by, deposited_at 
                FROM guild_bank 
                WHERE guild_id = ?
            """, (self.guild_id,))
            
            for row in cursor.fetchall():
                self.bank[row[0]] = GuildBankItem(
                    item_id=row[0],
                    quantity=row[1],
                    deposited_by=row[2],
                    deposited_at=datetime.fromisoformat(row[3])
                )
            
            # Баланс гильдии
            cursor.execute("SELECT balance FROM guild_bank_balance WHERE guild_id = ?", (self.guild_id,))
            balance = cursor.fetchone()
            self.bank_balance = balance[0] if balance else 0

    def save_guild_data(self):
        """Сохранить данные гильдии в БД"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Основная информация
            cursor.execute("""
                UPDATE guilds 
                SET name = ?, tag = ?, level = ?, exp = ?, motd = ?
                WHERE id = ?
            """, (self.name, self.tag, self.level, self.exp, self.motd, self.guild_id))
            
            # Удалить старых участников
            cursor.execute("DELETE FROM guild_members WHERE guild_id = ?", (self.guild_id,))
            
            # Добавить текущих участников
            for member in self.members.values():
                cursor.execute("""
                    INSERT INTO guild_members 
                    (guild_id, user_id, rank, joined_at, contribution, last_online)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.guild_id,
                    member.user_id,
                    member.rank.value,
                    member.joined_at.isoformat(),
                    member.contribution,
                    member.last_online.isoformat()
                ))
            
            # Банк гильдии
            cursor.execute("DELETE FROM guild_bank WHERE guild_id = ?", (self.guild_id,))
            
            for item in self.bank.values():
                cursor.execute("""
                    INSERT INTO guild_bank 
                    (guild_id, item_id, quantity, deposited_by, deposited_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    self.guild_id,
                    item.item_id,
                    item.quantity,
                    item.deposited_by,
                    item.deposited_at.isoformat()
                ))
            
            # Баланс
            cursor.execute("""
                INSERT OR REPLACE INTO guild_bank_balance 
                (guild_id, balance) 
                VALUES (?, ?)
            """, (self.guild_id, self.bank_balance))
            
            conn.commit()

    def add_member(self, user_id: int, rank: GuildRank = GuildRank.RECRUIT) -> bool:
        """Добавить нового участника в гильдию"""
        if user_id in self.members:
            return False
            
        if len(self.members) >= self.get_max_members():
            return False
            
        self.members[user_id] = GuildMember(
            user_id=user_id,
            rank=rank,
            joined_at=datetime.now(),
            contribution=0,
            last_online=datetime.now()
        )
        return True

    def remove_member(self, user_id: int) -> bool:
        """Удалить участника из гильдии"""
        if user_id not in self.members:
            return False
            
        del self.members[user_id]
        return True

    def promote_member(self, user_id: int) -> bool:
        """Повысить ранг участника"""
        if user_id not in self.members:
            return False
            
        current_rank = self.members[user_id].rank
        if current_rank == GuildRank.LEADER:
            return False
            
        self.members[user_id].rank = GuildRank(current_rank.value + 1)
        return True

    def demote_member(self, user_id: int) -> bool:
        """Понизить ранг участника"""
        if user_id not in self.members:
            return False
            
        current_rank = self.members[user_id].rank
        if current_rank == GuildRank.RECRUIT:
            return False
            
        self.members[user_id].rank = GuildRank(current_rank.value - 1)
        return True

    def get_max_members(self) -> int:
        """Максимальное количество участников в гильдии"""
        return 10 + self.level * 5

    def add_exp(self, amount: int):
        """Добавить гильдии опыта"""
        self.exp += amount
        required_exp = self.get_exp_for_next_level()
        
        if self.exp >= required_exp:
            self.level_up()

    def level_up(self):
        """Повысить уровень гильдии"""
        self.level += 1
        self.exp = 0
        # Можно добавить уведомления и награды за повышение уровня

    def get_exp_for_next_level(self) -> int:
        """Получить необходимое количество опыта для следующего уровня"""
        return 1000 * (2 ** (self.level - 1))

    def deposit_to_bank(self, user_id: int, item_id: str, quantity: int) -> bool:
        """Положить предмет в банк гильдии"""
        if item_id in self.bank:
            self.bank[item_id].quantity += quantity
        else:
            self.bank[item_id] = GuildBankItem(
                item_id=item_id,
                quantity=quantity,
                deposited_by=user_id,
                deposited_at=datetime.now()
            )
        
        # Увеличить вклад участника
        if user_id in self.members:
            self.members[user_id].contribution += quantity * 10
            
        return True

    def withdraw_from_bank(self, user_id: int, item_id: str, quantity: int) -> bool:
        """Взять предмет из банка гильдии"""
        if item_id not in self.bank or self.bank[item_id].quantity < quantity:
            return False
            
        # Проверка прав (офицеры и выше могут брать)
        if user_id in self.members and self.members[user_id].rank.value >= GuildRank.OFFICER.value:
            self.bank[item_id].quantity -= quantity
            if self.bank[item_id].quantity <= 0:
                del self.bank[item_id]
            return True
            
        return False

    def get_member_info(self, user_id: int) -> Optional[Dict]:
        """Получить информацию об участнике"""
        if user_id not in self.members:
            return None
            
        member = self.members[user_id]
        return {
            'user_id': member.user_id,
            'rank': member.rank.name,
            'joined_at': member.joined_at,
            'contribution': member.contribution,
            'last_online': member.last_online,
            'online': (datetime.now() - member.last_online) < timedelta(minutes=5)
        }

class GuildManager:
    def __init__(self, db: Database):
        self.db = db
        self.guilds: Dict[int, Guild] = {}
        self.load_all_guilds()

    def load_all_guilds(self):
        """Загрузить все гильдии из БД"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM guilds")
            
            for row in cursor.fetchall():
                guild_id = row[0]
                try:
                    self.guilds[guild_id] = Guild(self.db, guild_id)
                except Exception as e:
                    logger.error(f"Failed to load guild {guild_id}: {e}")

    def create_guild(self, leader_id: int, name: str, tag: str) -> Optional[Guild]:
        """Создать новую гильдию"""
        if len(tag) > 4 or len(name) > 24:
            return None
            
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверить уникальность имени и тега
            cursor.execute("SELECT 1 FROM guilds WHERE name = ? OR tag = ?", (name, tag))
            if cursor.fetchone():
                return None
                
            # Создать гильдию
            cursor.execute("""
                INSERT INTO guilds (name, tag, level, exp, created_at, motd)
                VALUES (?, ?, 1, 0, ?, 'Добро пожаловать в новую гильдию!')
            """, (name, tag, datetime.now().isoformat()))
            
            guild_id = cursor.lastrowid
            
            # Добавить лидера
            cursor.execute("""
                INSERT INTO guild_members 
                (guild_id, user_id, rank, joined_at, contribution, last_online)
                VALUES (?, ?, ?, ?, 0, ?)
            """, (guild_id, leader_id, GuildRank.LEADER.value, datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.commit()
            
            # Загрузить новую гильдию в менеджер
            new_guild = Guild(self.db, guild_id)
            self.guilds[guild_id] = new_guild
            return new_guild

    def disband_guild(self, guild_id: int, leader_id: int) -> bool:
        """Распустить гильдию"""
        if guild_id not in self.guilds:
            return False
            
        guild = self.guilds[guild_id]
        
        # Проверить, что запрашивающий является лидером
        if leader_id not in guild.members or guild.members[leader_id].rank != GuildRank.LEADER:
            return False
            
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Удалить все связанные данные
            cursor.execute("DELETE FROM guilds WHERE id = ?", (guild_id,))
            cursor.execute("DELETE FROM guild_members WHERE guild_id = ?", (guild_id,))
            cursor.execute("DELETE FROM guild_bank WHERE guild_id = ?", (guild_id,))
            cursor.execute("DELETE FROM guild_bank_balance WHERE guild_id = ?", (guild_id,))
            
            conn.commit()
            
            # Удалить из менеджера
            del self.guilds[guild_id]
            return True

    def get_guild_by_member(self, user_id: int) -> Optional[Guild]:
        """Получить гильдию по ID участника"""
        for guild in self.guilds.values():
            if user_id in guild.members:
                return guild
        return None

    def search_guilds(self, query: str, limit: int = 10) -> List[Dict]:
        """Поиск гильдий по названию или тегу"""
        results = []
        query = query.lower()
        
        for guild in self.guilds.values():
            if query in guild.name.lower() or query in guild.tag.lower():
                results.append({
                    'id': guild.guild_id,
                    'name': guild.name,
                    'tag': guild.tag,
                    'level': guild.level,
                    'member_count': len(guild.members),
                    'created_at': guild.created_at
                })
                
                if len(results) >= limit:
                    break
                    
        return results
