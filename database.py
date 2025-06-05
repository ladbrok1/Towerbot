############################
### database.py - Работа с базой данных ###
############################
"""
Модуль работы с базой данных:
- Инициализация БД
- Управление игроками
- Серверный прогресс
- Онлайн-статус
"""
import sqlite3
import json
import time

def init_db():
    conn = sqlite3.connect('mmorpg.db')
    cursor = conn.cursor()
    
    # Таблица игроков
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
        player_id INTEGER PRIMARY KEY,
        player_data TEXT NOT NULL,
        last_active REAL DEFAULT 0,
        guild_id INTEGER DEFAULT 0
    )''')
    
    # Таблица серверного прогресса
    cursor.execute('''CREATE TABLE IF NOT EXISTS server_progress (
        id INTEGER PRIMARY KEY DEFAULT 1,
        current_floor INTEGER DEFAULT 1,
        boss_hp INTEGER DEFAULT 1000,
        check (id = 1)
    )''')
    
    # Таблица гильдий
    cursor.execute('''CREATE TABLE IF NOT EXISTS guilds (
        guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        leader_id INTEGER NOT NULL,
        level INTEGER DEFAULT 1,
        reputation INTEGER DEFAULT 0,
        members TEXT DEFAULT '[]'
    )''')
    
    # Таблица PvP рейтингов
    cursor.execute('''CREATE TABLE IF NOT EXISTS pvp_ratings (
        player_id INTEGER PRIMARY KEY,
        rating INTEGER DEFAULT 1000,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0
    )''')
    
    # Проверяем и инициализируем прогресс сервера
    cursor.execute('SELECT 1 FROM server_progress WHERE id = 1')
    if not cursor.fetchone():
        cursor.execute('INSERT INTO server_progress (current_floor, boss_hp) VALUES (1, 1000)')
    
    conn.commit()
    conn.close()

def save_player(player_id, player_data):
    conn = sqlite3.connect('mmorpg.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO players (player_id, player_data, last_active) VALUES (?, ?, ?)', 
                  (player_id, json.dumps(player_data), time.time()))
    conn.commit()
    conn.close()

def load_player(player_id):
    conn = sqlite3.connect('mmorpg.db')
    cursor = conn.cursor()
    cursor.execute('SELECT player_data FROM players WHERE player_id = ?', (player_id,))
    result = cursor.fetchone()
    conn.close()
    return json.loads(result[0]) if result else None

def get_online_players(floor, exclude_id=None):
    conn = sqlite3.connect('mmorpg.db')
    cursor = conn.cursor()
    five_min_ago = time.time() - 300  # 5 минут
    cursor.execute('SELECT player_id FROM players WHERE last_active > ?', (five_min_ago,))
    online_ids = [row[0] for row in cursor.fetchall()]
    
    online_players = []
    for player_id in online_ids:
        if exclude_id is not None and player_id == exclude_id:
            continue
        player_data = load_player(player_id)
        if player_data and player_data["floor"] == floor and player_data["state"] == "idle":
            online_players.append(player_data)
    
    conn.close()
    return online_players

def get_server_progress():
    conn = sqlite3.connect('mmorpg.db')
    cursor = conn.cursor()
    cursor.execute('SELECT current_floor, boss_hp FROM server_progress WHERE id = 1')
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "current_floor": result[0],
            "boss_hp": result[1]
        }
    return {"current_floor": 1, "boss_hp": 1000}

def update_server_progress(progress):
    conn = sqlite3.connect('mmorpg.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE server_progress SET current_floor = ?, boss_hp = ? WHERE id = 1', 
                  (progress["current_floor"], progress["boss_hp"]))
    conn.commit()
    conn.close()

def get_guild(guild_id):
    conn = sqlite3.connect('mmorpg.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM guilds WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def save_guild(guild_data):
    conn = sqlite3.connect('mmorpg.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO guilds (guild_id, name, leader_id, level, reputation, members) VALUES (?, ?, ?, ?, ?, ?)',
                  (guild_data['guild_id'], guild_data['name'], guild_data['leader_id'], 
                   guild_data['level'], guild_data['reputation'], json.dumps(guild_data['members'])))
    conn.commit()
    conn.close()

def get_pvp_rating(player_id):
    conn = sqlite3.connect('mmorpg.db')
    cursor = conn.cursor()
    cursor.execute('SELECT rating, wins, losses FROM pvp_ratings WHERE player_id = ?', (player_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"rating": result[0], "wins": result[1], "losses": result[2]}
    return None

def update_pvp_rating(player_id, rating, wins, losses):
    conn = sqlite3.connect('mmorpg.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO pvp_ratings (player_id, rating, wins, losses) VALUES (?, ?, ?, ?)',
                  (player_id, rating, wins, losses))
    conn.commit()
    conn.close()