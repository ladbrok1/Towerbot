import sqlite3
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "game.db"):
        self.db_path = db_path
        self.connection = None
        self._initialize_db()

    def _initialize_db(self):
        """Инициализировать базу данных и создать таблицы"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Таблица игроков
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS players (
                        player_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        level INTEGER DEFAULT 1,
                        exp INTEGER DEFAULT 0,
                        gold INTEGER DEFAULT 0,
                        health INTEGER DEFAULT 100,
                        max_health INTEGER DEFAULT 100,
                        attack INTEGER DEFAULT 10,
                        defense INTEGER DEFAULT 5,
                        inventory TEXT DEFAULT '{}',
                        skills TEXT DEFAULT '{}',
                        guild_id INTEGER,
                        last_seen TEXT,
                        FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
                    )
                ''')
                
                # Таблица гильдий
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS guilds (
                        guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        tag TEXT NOT NULL,
                        level INTEGER DEFAULT 1,
                        created_at TEXT NOT NULL
                    )
                ''')
                
                # Таблица гильдейских участников
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS guild_members (
                        guild_id INTEGER NOT NULL,
                        player_id INTEGER NOT NULL,
                        rank TEXT NOT NULL,
                        joined_at TEXT NOT NULL,
                        PRIMARY KEY (guild_id, player_id),
                        FOREIGN KEY (guild_id) REFERENCES guilds(guild_id),
                        FOREIGN KEY (player_id) REFERENCES players(player_id)
                    )
                ''')
                
                # Таблица предметов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS items (
                        item_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        stats TEXT DEFAULT '{}',
                        price INTEGER DEFAULT 0
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def get_connection(self):
        """Получить соединение с базой данных"""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
        return self.connection

    def close_connection(self):
        """Закрыть соединение с базой данных"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute_query(self, query: str, params: tuple = (), commit: bool = False):
        """Выполнить SQL-запрос"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            return cursor
        except sqlite3.Error as e:
            logger.error(f"Query execution error: {e}")
            raise

    # Примеры методов для работы с игроками
    def create_player(self, player_id: int, name: str):
        """Создать нового игрока"""
        self.execute_query(
            '''
            INSERT INTO players (player_id, name, last_seen)
            VALUES (?, ?, datetime('now'))
            ''',
            (player_id, name),
            commit=True
        )

    def get_player(self, player_id: int) -> Optional[Dict]:
        """Получить данные игрока"""
        cursor = self.execute_query(
            'SELECT * FROM players WHERE player_id = ?',
            (player_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_player(self, player_id: int, updates: Dict):
        """Обновить данные игрока"""
        set_clause = ', '.join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values())
        values.append(player_id)
        
        self.execute_query(
            f'''
            UPDATE players 
            SET {set_clause}, last_seen = datetime('now')
            WHERE player_id = ?
            ''',
            tuple(values),
            commit=True
        )

       # Методы для работы с гильдиями
    def create_guild(self, name: str, tag: str, leader_id: int) -> int:
        """Создать новую гильдию"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO guilds (name, tag, created_at)
                    VALUES (?, ?, datetime('now'))
                    ''',
                    (name, tag)
                guild_id = cursor.lastrowid
                
                # Добавить лидера в гильдию
                cursor.execute(
                    '''
                    INSERT INTO guild_members (guild_id, player_id, rank, joined_at)
                    VALUES (?, ?, 'leader', datetime('now'))
                    ''',
                    (guild_id, leader_id))
                
                # Обновить гильдию игрока
                cursor.execute(
                    '''
                    UPDATE players 
                    SET guild_id = ? 
                    WHERE player_id = ?
                    ''',
                    (guild_id, leader_id))
                
                conn.commit()
                return guild_id
        except sqlite3.Error as e:
            logger.error(f"Error creating guild: {e}")
            raise

    def get_guild(self, guild_id: int) -> Optional[Dict]:
        """Получить информацию о гильдии"""
        cursor = self.execute_query(
            '''
            SELECT g.*, 
                   COUNT(gm.player_id) as member_count
            FROM guilds g
            LEFT JOIN guild_members gm ON g.guild_id = gm.guild_id
            WHERE g.guild_id = ?
            GROUP BY g.guild_id
            ''',
            (guild_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_guild_members(self, guild_id: int) -> List[Dict]:
        """Получить список участников гильдии"""
        cursor = self.execute_query(
            '''
            SELECT p.player_id, p.name, p.level, gm.rank, gm.joined_at
            FROM guild_members gm
            JOIN players p ON gm.player_id = p.player_id
            WHERE gm.guild_id = ?
            ORDER BY 
                CASE gm.rank
                    WHEN 'leader' THEN 1
                    WHEN 'officer' THEN 2
                    WHEN 'member' THEN 3
                    ELSE 4
                END,
                gm.joined_at
            ''',
            (guild_id,))
        return [dict(row) for row in cursor.fetchall()]

    # Методы для работы с инвентарем
    def get_player_inventory(self, player_id: int) -> Dict[str, int]:
        """Получить инвентарь игрока"""
        player = self.get_player(player_id)
        if player and 'inventory' in player:
            return json.loads(player['inventory'])
        return {}

    def update_player_inventory(self, player_id: int, inventory: Dict[str, int]):
        """Обновить инвентарь игрока"""
        self.execute_query(
            '''
            UPDATE players 
            SET inventory = ?
            WHERE player_id = ?
            ''',
            (json.dumps(inventory), player_id),
            commit=True)

    def add_item_to_inventory(self, player_id: int, item_id: str, quantity: int = 1):
        """Добавить предмет в инвентарь"""
        inventory = self.get_player_inventory(player_id)
        inventory[item_id] = inventory.get(item_id, 0) + quantity
        self.update_player_inventory(player_id, inventory)

    # Методы для работы с предметами
    def get_item_info(self, item_id: str) -> Optional[Dict]:
        """Получить информацию о предмете"""
        cursor = self.execute_query(
            'SELECT * FROM items WHERE item_id = ?',
            (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_item(self, item_data: Dict):
        """Создать новый предмет в базе"""
        self.execute_query(
            '''
            INSERT INTO items (item_id, name, type, stats, price)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                item_data['id'],
                item_data['name'],
                item_data['type'],
                json.dumps(item_data.get('stats', {})),
                item_data.get('price', 0)
            ),
            commit=True)

    # Методы для работы с квестами
    def init_quests_table(self):
        """Инициализировать таблицу квестов"""
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS player_quests (
                player_id INTEGER NOT NULL,
                quest_id TEXT NOT NULL,
                status TEXT NOT NULL,  -- 'not_started', 'in_progress', 'completed'
                progress TEXT DEFAULT '{}',
                started_at TEXT,
                completed_at TEXT,
                PRIMARY KEY (player_id, quest_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        ''', commit=True)

    def get_player_quests(self, player_id: int) -> List[Dict]:
        """Получить квесты игрока"""
        cursor = self.execute_query(
            '''
            SELECT quest_id, status, progress, started_at, completed_at
            FROM player_quests
            WHERE player_id = ?
            ''',
            (player_id,))
        return [dict(row) for row in cursor.fetchall()]

    def update_quest_progress(self, player_id: int, quest_id: str, progress: Dict):
        """Обновить прогресс квеста"""
        self.execute_query(
            '''
            INSERT OR REPLACE INTO player_quests 
            (player_id, quest_id, status, progress, started_at)
            VALUES (?, ?, 'in_progress', ?, COALESCE(
                (SELECT started_at FROM player_quests WHERE player_id = ? AND quest_id = ?),
                datetime('now')
            ))
            ''',
            (player_id, quest_id, json.dumps(progress), player_id, quest_id),
            commit=True)

    # Методы для работы с PvP
    def init_pvp_tables(self):
        """Инициализировать таблицы PvP статистики"""
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS pvp_stats (
                player_id INTEGER PRIMARY KEY,
                kills INTEGER DEFAULT 0,
                deaths INTEGER DEFAULT 0,
                honor INTEGER DEFAULT 0,
                last_pvp_time TEXT,
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        ''', commit=True)

    def update_pvp_stats(self, player_id: int, kills: int = 0, deaths: int = 0, honor: int = 0):
        """Обновить PvP статистику игрока"""
        self.execute_query(
            '''
            INSERT OR REPLACE INTO pvp_stats 
            (player_id, kills, deaths, honor, last_pvp_time)
            VALUES (?, 
                COALESCE((SELECT kills FROM pvp_stats WHERE player_id = ?), 0) + ?,
                COALESCE((SELECT deaths FROM pvp_stats WHERE player_id = ?), 0) + ?,
                COALESCE((SELECT honor FROM pvp_stats WHERE player_id = ?), 0) + ?,
                datetime('now'))
            ''',
            (player_id, player_id, kills, player_id, deaths, player_id, honor),
            commit=True)

    # Методы для работы с рейдами
    def init_raid_tables(self):
        """Инициализировать таблицы рейдов"""
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS raid_history (
                raid_id TEXT PRIMARY KEY,
                boss_id TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL  -- 'completed', 'failed'
            )
        ''', commit=True)

        self.execute_query('''
            CREATE TABLE IF NOT EXISTS raid_participants (
                raid_id TEXT NOT NULL,
                player_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                damage_done INTEGER DEFAULT 0,
                healing_done INTEGER DEFAULT 0,
                loot_received TEXT DEFAULT '[]',
                PRIMARY KEY (raid_id, player_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        ''', commit=True)

    def save_raid_result(self, raid_data: Dict):
        """Сохранить результаты рейда"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Сохранить основную информацию о рейде
            cursor.execute(
                '''
                INSERT INTO raid_history 
                (raid_id, boss_id, difficulty, start_time, end_time, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    raid_data['raid_id'],
                    raid_data['boss_id'],
                    raid_data['difficulty'],
                    raid_data['start_time'],
                    raid_data['end_time'],
                    raid_data['status']
                ))
            
            # Сохранить данные участников
            for participant in raid_data['participants']:
                cursor.execute(
                    '''
                    INSERT INTO raid_participants 
                    (raid_id, player_id, role, damage_done, healing_done, loot_received)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        raid_data['raid_id'],
                        participant['player_id'],
                        participant['role'],
                        participant.get('damage_done', 0),
                        participant.get('healing_done', 0),
                        json.dumps(participant.get('loot_received', []))
                    ))
            
            conn.commit()

    # Методы для работы с экономикой
    def init_economy_tables(self):
        """Инициализировать таблицы экономики"""
        self.execute_query('''
            CREATE TABLE IF NOT EXISTS market_listings (
                listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price INTEGER NOT NULL,
                currency TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (seller_id) REFERENCES players(player_id)
            )
        ''', commit=True)

    def create_market_listing(self, seller_id: int, item_id: str, quantity: int, 
                            price: int, currency: str, duration_hours: int = 24):
        """Создать новое предложение на рынке"""
        self.execute_query(
            '''
            INSERT INTO market_listings 
            (seller_id, item_id, quantity, price, currency, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now', ?))
            ''',
            (seller_id, item_id, quantity, price, currency, f"+{duration_hours} hours"),
            commit=True)

    def get_active_listings(self, item_id: Optional[str] = None) -> List[Dict]:
        """Получить активные предложения на рынке"""
        query = '''
            SELECT l.*, p.name as seller_name
            FROM market_listings l
            JOIN players p ON l.seller_id = p.player_id
            WHERE datetime('now') < l.expires_at
        '''
        params = ()
        
        if item_id:
            query += ' AND l.item_id = ?'
            params = (item_id,)
            
        query += ' ORDER BY l.price ASC'
        
        cursor = self.execute_query(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # Утилитные методы
    def backup_database(self, backup_path: str):
        """Создать резервную копию базы данных"""
        try:
            with self.get_connection() as conn:
                with open(backup_path, 'w') as f:
                    for line in conn.iterdump():
                        f.write(f'{line}\n')
            logger.info(f"Database backup created at {backup_path}")
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise

# Инициализация синглтона базы данных
db_instance = Database()
