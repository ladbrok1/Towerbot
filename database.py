############################
### database.py - Работа с базой данных ###
############################
"""
Модуль работы с базой данных:
- Инициализация БД
- Управление игроками
- Серверный прогресс
- Онлайн-статус
- Глобальные события
"""
import sqlite3
import json
import time
import logging
from typing import Optional, Dict, List, Union, Tuple

# Настройка логирования
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str = 'mmorpg.db'):
        self.db_name = db_name
        self.conn = None
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Инициализация базы данных и таблиц"""
        try:
            self.conn = sqlite3.connect(self.db_name)
            cursor = self.conn.cursor()
            
            # Таблица игроков
            cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY,
                player_data TEXT NOT NULL,
                last_active REAL DEFAULT 0,
                guild_id INTEGER DEFAULT 0,
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
            ''')
            
            # Таблица серверного прогресса
            cursor.execute('''CREATE TABLE IF NOT EXISTS server_progress (
                id INTEGER PRIMARY KEY DEFAULT 1,
                current_floor INTEGER DEFAULT 1,
                boss_hp INTEGER DEFAULT 1000,
                last_boss_kill REAL DEFAULT 0,
                check (id = 1)
            ''')
            
            # Таблица гильдий
            cursor.execute('''CREATE TABLE IF NOT EXISTS guilds (
                guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                leader_id INTEGER NOT NULL,
                level INTEGER DEFAULT 1,
                reputation INTEGER DEFAULT 0,
                members TEXT DEFAULT '[]',
                FOREIGN KEY (leader_id) REFERENCES players(player_id))
            ''')
            
            # Таблица PvP рейтингов
            cursor.execute('''CREATE TABLE IF NOT EXISTS pvp_ratings (
                player_id INTEGER PRIMARY KEY,
                rating INTEGER DEFAULT 1000,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                FOREIGN KEY (player_id) REFERENCES players(player_id))
            ''')
            
            # Таблица глобальных событий (новая)
            cursor.execute('''CREATE TABLE IF NOT EXISTS global_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                event_data TEXT DEFAULT '{}')
            ''')
            
            # Инициализация серверного прогресса
            cursor.execute('SELECT 1 FROM server_progress WHERE id = 1')
            if not cursor.fetchone():
                cursor.execute('INSERT INTO server_progress (current_floor, boss_hp) VALUES (1, 1000)')
            
            self.conn.commit()
            logger.info("База данных успешно инициализирована")
        except sqlite3.Error as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
        finally:
            if self.conn:
                self.conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Получение соединения с БД"""
        if not self.conn:
            self.conn = sqlite3.connect(self.db_name)
        return self.conn

    def save_player(self, player_id: int, player_data: Dict) -> bool:
        """Сохранение данных игрока"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO players 
                            (player_id, player_data, last_active) 
                            VALUES (?, ?, ?)''', 
                         (player_id, json.dumps(player_data), time.time()))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка сохранения игрока {player_id}: {e}")
            return False

    def load_player(self, player_id: int) -> Optional[Dict]:
        """Загрузка данных игрока"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT player_data FROM players WHERE player_id = ?', (player_id,))
            result = cursor.fetchone()
            return json.loads(result[0]) if result else None
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Ошибка загрузки игрока {player_id}: {e}")
            return None

    def get_online_players(self, floor: int, exclude_id: Optional[int] = None) -> List[Dict]:
        """Получение списка онлайн игроков на указанном этаже"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            five_min_ago = time.time() - 300  # 5 минут
            cursor.execute('SELECT player_id FROM players WHERE last_active > ?', (five_min_ago,))
            online_ids = [row[0] for row in cursor.fetchall()]
            
            online_players = []
            for player_id in online_ids:
                if exclude_id is not None and player_id == exclude_id:
                    continue
                player_data = self.load_player(player_id)
                if player_data and player_data.get("floor") == floor and player_data.get("state") == "idle":
                    online_players.append(player_data)
            
            return online_players
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения онлайн игроков: {e}")
            return []

    def get_server_progress(self) -> Dict[str, Union[int, float]]:
        """Получение серверного прогресса"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT current_floor, boss_hp, last_boss_kill FROM server_progress WHERE id = 1')
            result = cursor.fetchone()
            
            if result:
                return {
                    "current_floor": result[0],
                    "boss_hp": result[1],
                    "last_boss_kill": result[2] or 0
                }
            return {"current_floor": 1, "boss_hp": 1000, "last_boss_kill": 0}
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения серверного прогресса: {e}")
            return {"current_floor": 1, "boss_hp": 1000, "last_boss_kill": 0}

    def update_server_progress(self, progress: Dict) -> bool:
        """Обновление серверного прогресса"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''UPDATE server_progress 
                            SET current_floor = ?, boss_hp = ?, last_boss_kill = ?
                            WHERE id = 1''', 
                         (progress.get("current_floor", 1),
                          progress.get("boss_hp", 1000),
                          progress.get("last_boss_kill", 0)))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления серверного прогресса: {e}")
            return False

    # Далее идут методы для работы с гильдиями, PvP и глобальными событиями
    # (приведены основные изменения, полный код будет в следующем сообщении)

    def get_guild(self, guild_id: int) -> Optional[Dict]:
        """Получение данных гильдии"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM guilds WHERE guild_id = ?', (guild_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'guild_id': result[0],
                    'name': result[1],
                    'leader_id': result[2],
                    'level': result[3],
                    'reputation': result[4],
                    'members': json.loads(result[5])
                }
            return None
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Ошибка получения гильдии {guild_id}: {e}")
            return None

    def save_guild(self, guild_data: Dict) -> bool:
        """Сохранение данных гильдии"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO guilds 
                            (guild_id, name, leader_id, level, reputation, members) 
                            VALUES (?, ?, ?, ?, ?, ?)''',
                          (guild_data.get('guild_id'),
                           guild_data.get('name'),
                           guild_data.get('leader_id'),
                           guild_data.get('level', 1),
                           guild_data.get('reputation', 0),
                           json.dumps(guild_data.get('members', []))))
            conn.commit()
            return True
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Ошибка сохранения гильдии: {e}")
            return False

    def get_pvp_rating(self, player_id: int) -> Optional[Dict]:
        """Получение PvP рейтинга игрока"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT rating, wins, losses FROM pvp_ratings WHERE player_id = ?', (player_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    "rating": result[0],
                    "wins": result[1],
                    "losses": result[2]
                }
            return None
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения PvP рейтинга для {player_id}: {e}")
            return None

    def update_pvp_rating(self, player_id: int, rating: int, wins: int, losses: int) -> bool:
        """Обновление PvP рейтинга игрока"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO pvp_ratings 
                            (player_id, rating, wins, losses) 
                            VALUES (?, ?, ?, ?)''',
                          (player_id, rating, wins, losses))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления PvP рейтинга для {player_id}: {e}")
            return False

    # Методы для работы с глобальными событиями (новые)
    def create_global_event(self, event_type: str, duration: float, event_data: Dict = {}) -> bool:
        """Создание глобального события"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            start_time = time.time()
            end_time = start_time + duration
            
            cursor.execute('''INSERT INTO global_events 
                            (event_type, start_time, end_time, event_data) 
                            VALUES (?, ?, ?, ?)''',
                          (event_type, start_time, end_time, json.dumps(event_data)))
            conn.commit()
            return True
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Ошибка создания события {event_type}: {e}")
            return False

    def get_active_events(self) -> List[Dict]:
        """Получение активных глобальных событий"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            current_time = time.time()
            
            cursor.execute('''SELECT event_id, event_type, start_time, end_time, event_data 
                            FROM global_events 
                            WHERE start_time <= ? AND end_time >= ?''',
                          (current_time, current_time))
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    'event_id': row[0],
                    'event_type': row[1],
                    'start_time': row[2],
                    'end_time': row[3],
                    'event_data': json.loads(row[4])
                })
            
            return events
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.error(f"Ошибка получения активных событий: {e}")
            return []
# Глобальный экземпляр базы данных для обратной совместимости
db_instance = Database()

def init_db():
    """Функция для обратной совместимости"""
    return db_instance._initialize_db()

def save_player(player_id, player_data):
    return db_instance.save_player(player_id, player_data)

def load_player(player_id):
    return db_instance.load_player(player_id)

# ... остальные функции для обратной совместимости ...
