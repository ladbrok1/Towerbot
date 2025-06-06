import logging
import random
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime
from pathlib import Path
from database import Database

logger = logging.getLogger(__name__)

class BiomeType(Enum):
    FOREST = auto()
    MOUNTAIN = auto()
    DESERT = auto()
    SWAMP = auto()
    TUNDRA = auto()
    RUINS = auto()
    DUNGEON = auto()
    CITY = auto()

class LocationType(Enum):
    TOWN = auto()
    DUNGEON = auto()
    QUEST_HUB = auto()
    RESOURCE_NODE = auto()
    BOSS_ARENA = auto()
    PVP_ZONE = auto()

@dataclass
class WorldLocation:
    x: int
    y: int
    name: str
    biome: BiomeType
    loc_type: LocationType
    level_range: Tuple[int, int]
    discovered_by: Dict[int, datetime]  # player_id: discovery_time
    special_features: Dict[str, bool]
    npcs: List[int]
    resources: Dict[str, float]  # resource_type: spawn_chance
    enemies: Dict[str, float]    # enemy_type: spawn_chance

class WorldManager:
    def __init__(self, db: Database, config_path: str = "world_config.json"):
        self.db = db
        self.locations: Dict[Tuple[int, int], WorldLocation] = {}
        self.player_positions: Dict[int, Tuple[int, int]] = {}  # player_id: (x, y)
        self.world_size = (1000, 1000)  # width, height
        self._load_config(config_path)
        self._initialize_world()
        self._load_player_positions()

    def _load_config(self, config_path: str):
        """Загрузить конфигурацию мира из файла"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.world_size = (config['world_width'], config['world_height'])
                self.biome_distribution = config['biome_distribution']
                self.starting_location = tuple(config['starting_location'])
        except Exception as e:
            logger.error(f"Failed to load world config: {e}")
            raise

    def _initialize_world(self):
        """Инициализировать базовые локации мира"""
        # Стартовая локация
        self._generate_location(
            x=self.starting_location[0],
            y=self.starting_location[1],
            name="Начальный город",
            biome=BiomeType.CITY,
            loc_type=LocationType.TOWN,
            level_range=(1, 10)
        )

        # Генерация дополнительных локаций
        for _ in range(50):
            x = random.randint(0, self.world_size[0] - 1)
            y = random.randint(0, self.world_size[1] - 1)
            if (x, y) not in self.locations:
                self._generate_random_location(x, y)

    def _generate_random_location(self, x: int, y: int):
        """Сгенерировать случайную локацию"""
        # Определить биом
        biome = self._determine_biome(x, y)
        
        # Определить тип локации на основе биома
        if biome == BiomeType.CITY:
            loc_type = LocationType.TOWN
            name = f"Город {random.choice(['Северный', 'Восточный', 'Западный', 'Южный'])}"
            level_range = (1, 15)
        else:
            loc_type = random.choices(
                [LocationType.DUNGEON, LocationType.QUEST_HUB, LocationType.RESOURCE_NODE],
                weights=[0.2, 0.3, 0.5]
            )[0]
            name = self._generate_location_name(biome)
            level_range = self._determine_level_range(x, y)

        self._generate_location(
            x=x,
            y=y,
            name=name,
            biome=biome,
            loc_type=loc_type,
            level_range=level_range
        )

    def _generate_location(
        self,
        x: int,
        y: int,
        name: str,
        biome: BiomeType,
        loc_type: LocationType,
        level_range: Tuple[int, int]
    ):
        """Создать новую локацию"""
        location = WorldLocation(
            x=x,
            y=y,
            name=name,
            biome=biome,
            loc_type=loc_type,
            level_range=level_range,
            discovered_by={},
            special_features={},
            npcs=[],
            resources=self._get_biome_resources(biome),
            enemies=self._get_biome_enemies(biome)
        )
        self.locations[(x, y)] = location
        return location

    def _determine_biome(self, x: int, y: int) -> BiomeType:
        """Определить биом для координат"""
        # Простая реализация - можно заменить на шум Перлина или другую продвинутую генерацию
        distance_to_center = ((x - self.world_size[0]/2)**2 + (y - self.world_size[1]/2)**2)**0.5
        max_distance = (self.world_size[0]**2 + self.world_size[1]**2)**0.5 / 2

        if distance_to_center < max_distance * 0.2:
            return BiomeType.CITY
        
        rand_val = random.random()
        if rand_val < 0.3:
            return BiomeType.FOREST
        elif rand_val < 0.5:
            return BiomeType.MOUNTAIN
        elif rand_val < 0.65:
            return BiomeType.DESERT
        elif rand_val < 0.8:
            return BiomeType.SWAMP
        else:
            return BiomeType.TUNDRA

    def _get_biome_resources(self, biome: BiomeType) -> Dict[str, float]:
        """Получить ресурсы для биома"""
        resources = {
            BiomeType.FOREST: {
                "wood": 0.8,
                "herbs": 0.6,
                "berries": 0.4
            },
            BiomeType.MOUNTAIN: {
                "stone": 0.9,
                "iron_ore": 0.5,
                "precious_gems": 0.1
            },
            BiomeType.DESERT: {
                "sand": 0.7,
                "cactus": 0.4,
                "fossils": 0.2
            },
            BiomeType.SWAMP: {
                "mushrooms": 0.6,
                "frog_legs": 0.3,
                "rare_herbs": 0.2
            },
            BiomeType.TUNDRA: {
                "ice": 0.7,
                "arctic_herbs": 0.4,
                "fur": 0.5
            },
            BiomeType.CITY: {
                "trade_goods": 0.3,
                "food": 0.5
            }
        }
        return resources.get(biome, {})

    def _get_biome_enemies(self, biome: BiomeType) -> Dict[str, float]:
        """Получить врагов для биома"""
        enemies = {
            BiomeType.FOREST: {
                "wolf": 0.6,
                "bandit": 0.4,
                "forest_spider": 0.3
            },
            BiomeType.MOUNTAIN: {
                "mountain_troll": 0.5,
                "eagle": 0.3,
                "rock_golem": 0.2
            },
            BiomeType.DESERT: {
                "scorpion": 0.7,
                "mummy": 0.4,
                "sand_worm": 0.1
            },
            BiomeType.SWAMP: {
                "swamp_monster": 0.6,
                "poison_snake": 0.5,
                "ghost": 0.3
            },
            BiomeType.TUNDRA: {
                "ice_wolf": 0.7,
                "yeti": 0.3,
                "frost_mage": 0.2
            },
            BiomeType.CITY: {
                "thief": 0.1
            }
        }
        return enemies.get(biome, {})

    def _generate_location_name(self, biome: BiomeType) -> str:
        """Сгенерировать название локации"""
        prefixes = {
            BiomeType.FOREST: ["Темный", "Зачарованный", "Древний", "Мрачный"],
            BiomeType.MOUNTAIN: ["Высокий", "Опасный", "Забытый", "Ледяной"],
            BiomeType.DESERT: ["Горячий", "Безжизненный", "Песчаный", "Выжженный"],
            BiomeType.SWAMP: ["Гнилой", "Туманный", "Ядовитый", "Заболоченный"],
            BiomeType.TUNDRA: ["Ледяной", "Северный", "Замерзший", "Бескрайний"]
        }
        nouns = {
            BiomeType.FOREST: ["Лес", "Роща", "Чаща", "Дуброва"],
            BiomeType.MOUNTAIN: ["Пик", "Перевал", "Хребет", "Утес"],
            BiomeType.DESERT: ["Оазис", "Каньон", "Пустошь", "Дюны"],
            BiomeType.SWAMP: ["Трясина", "Болото", "Топь", "Трясь"],
            BiomeType.TUNDRA: ["Равнина", "Долина", "Плато", "Земли"]
        }
        prefix = random.choice(prefixes.get(biome, [""]))
        noun = random.choice(nouns.get(biome, ["Место"]))
        return f"{prefix} {noun}"

    def _determine_level_range(self, x: int, y: int) -> Tuple[int, int]:
        """Определить уровень сложности локации"""
        distance = ((x - self.starting_location[0])**2 + (y - self.starting_location[1])**2)**0.5
        max_distance = (self.world_size[0]**2 + self.world_size[1]**2)**0.5
        level = min(50, max(1, int(distance / max_distance * 50)))
        return (level, level + 5)

    def _load_player_positions(self):
        """Загрузить позиции игроков из БД"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT player_id, x, y FROM player_positions")
            for row in cursor.fetchall():
                self.player_positions[row[0]] = (row[1], row[2])

    def save_player_position(self, player_id: int, x: int, y: int):
        """Сохранить позицию игрока"""
        self.player_positions[player_id] = (x, y)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO player_positions 
                (player_id, x, y) 
                VALUES (?, ?, ?)
            """, (player_id, x, y))
            conn.commit()

    def get_player_position(self, player_id: int) -> Tuple[int, int]:
        """Получить позицию игрока"""
        return self.player_positions.get(player_id, self.starting_location)

    def move_player(self, player_id: int, direction: str) -> Tuple[int, int]:
        """Переместить игрока в направлении"""
        x, y = self.get_player_position(player_id)
        
        directions = {
            "north": (0, 1),
            "south": (0, -1),
            "east": (1, 0),
            "west": (-1, 0),
            "northeast": (1, 1),
            "northwest": (-1, 1),
            "southeast": (1, -1),
            "southwest": (-1, -1)
        }
        
        dx, dy = directions.get(direction.lower(), (0, 0))
        new_x = max(0, min(self.world_size[0] - 1, x + dx))
        new_y = max(0, min(self.world_size[1] - 1, y + dy))
        
        self.save_player_position(player_id, new_x, new_y)
        return new_x, new_y

    def get_current_location(self, player_id: int) -> Optional[WorldLocation]:
        """Получить текущую локацию игрока"""
        x, y = self.get_player_position(player_id)
        return self.locations.get((x, y))

    def discover_location(self, player_id: int, x: int, y: int):
        """Зарегистрировать открытие локации игроком"""
        if (x, y) in self.locations and player_id not in self.locations[(x, y)].discovered_by:
            self.locations[(x, y)].discovered_by[player_id] = datetime.now()
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO player_discoveries 
                    (player_id, x, y, discovery_time) 
                    VALUES (?, ?, ?, ?)
                """, (player_id, x, y, datetime.now().isoformat()))
                conn.commit()

    def get_nearby_locations(self, x: int, y: int, radius: int = 5) -> List[WorldLocation]:
        """Получить ближайшие локации"""
        nearby = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if (x + dx, y + dy) in self.locations:
                    nearby.append(self.locations[(x + dx, y + dy)])
        return nearby

    def generate_dungeon(self, player_level: int) -> WorldLocation:
        """Сгенерировать подземелье для игрока"""
        dungeon_level = random.randint(player_level, player_level + 5)
        x, y = self._find_empty_spot()
        
        dungeon = self._generate_location(
            x=x,
            y=y,
            name=f"Подземелье Уровня {dungeon_level}",
            biome=BiomeType.DUNGEON,
            loc_type=LocationType.DUNGEON,
            level_range=(dungeon_level, dungeon_level + 2)
        )
        
        # Добавить специальные особенности
        dungeon.special_features = {
            "boss": True,
            "traps": random.random() > 0.3,
            "secret_rooms": random.randint(0, 3),
            "chests": random.randint(1, 5)
        }
        
        return dungeon

    def _find_empty_spot(self) -> Tuple[int, int]:
        """Найти пустое место на карте"""
        attempts = 0
        while attempts < 100:
            x = random.randint(0, self.world_size[0] - 1)
            y = random.randint(0, self.world_size[1] - 1)
            if (x, y) not in self.locations:
                return x, y
            attempts += 1
        return self.world_size[0] // 2, self.world_size[1] // 2

    def reset_world(self):
        """Перегенерировать мир (для админских целей)"""
        self.locations.clear()
        self._initialize_world()
        logger.info("World has been reset")

    def get_world_map_data(self, player_id: int, width: int = 20, height: int = 20) -> Dict:
        """Получить данные для отображения карты"""
        player_x, player_y = self.get_player_position(player_id)
        half_width = width // 2
        half_height = height // 2
        
        map_data = {
            "player_position": (player_x, player_y),
            "tiles": [],
            "discovered_locations": []
        }
        
        # Собрать информацию о тайлах
        for y in range(player_y - half_height, player_y + half_height + 1):
            row = []
            for x in range(player_x - half_width, player_x + half_width + 1):
                if 0 <= x < self.world_size[0] and 0 <= y < self.world_size[1]:
                    biome = self._determine_biome(x, y)
                    row.append({
                        "biome": biome.name,
                        "discovered": (x, y) in self.locations and player_id in self.locations[(x, y)].discovered_by
                    })
                else:
                    row.append({"biome": "VOID", "discovered": False})
            map_data["tiles"].append(row)
        
        # Собрать информацию о локациях
        for loc in self.locations.values():
            if player_id in loc.discovered_by:
                map_data["discovered_locations"].append({
                    "x": loc.x,
                    "y": loc.y,
                    "name": loc.name,
                    "type": loc.loc_type.name
                })
        
        return map_data
