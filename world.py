############################
### world.py - Игровой мир ###
############################
"""
Модуль игрового мира:
- Лор и описания
- Данные оружия и монстров
- Боссы и этажи
- Локации для исследования
- Магазин и предметы
- Таланты и эпические боссы
"""
# Игровой мир
world_lore = """
🌌 *Башня Тысячи Грез* 🌌

Давным-давно, когда боги еще ходили по земле, они воздвигли Башню - испытание для смертных. 
100 этажей, каждый - отдельный мир со своими законами, монстрами и сокровищами. 

Говорят, на вершине Башни ждет *Исполнение Любого Желания*. 
Но никто еще не дошел до 100-го этажа... 

Ты - один из смельчаков, кто решил бросить вызов Башне. 
Сможешь ли ты подняться выше всех?
"""

# Шаблон персонажа
player_template = {
    "nickname": "",
    "floor": 1,
    "level": 1,
    "exp": 0,
    "stats": {
        "strength": 5, 
        "agility": 5, 
        "vitality": 5, 
        "luck": 5, 
        "accuracy": 5, 
        "defense": 5
    },
    "weapons": {
        "sword": {"level": 0, "skills": [], "exp": 0, "talent_points": 0},
        "dagger": {"level": 0, "skills": [], "exp": 0, "talent_points": 0},
        "mace": {"level": 0, "skills": [], "exp": 0, "talent_points": 0},
        "bow": {"level": 0, "skills": [], "exp": 0, "talent_points": 0},
        "axe": {"level": 0, "skills": [], "exp": 0, "talent_points": 0},
        "spear": {"level": 0, "skills": [], "exp": 0, "talent_points": 0},
        "hammer": {"level": 0, "skills": [], "exp": 0, "talent_points": 0},
        "crossbow": {"level": 0, "skills": [], "exp": 0, "talent_points": 0}
    },
    "current_weapon": None,
    "inventory": [],
    "gold": 100,
    "hp": 100,
    "max_hp": 100,
    "state": "idle",  # idle/fighting/dueling/raiding
    "explored": 0,    # Процент исследования текущего этажа
    "deaths": 0,      # Счетчик смертей
    "talent_points": 0,
    "active_effects": [],
    "guild_id": 0,
    "pvp_rating": 1000,
    "pvp_wins": 0,
    "pvp_losses": 0
}

# Данные оружия
weapons_data = {
    "sword": {
        "name": "Меч",
        "damage": 8, 
        "base_skill": "Разящий удар",
        "stat": "strength",
        "skills": {
            "Силовой удар": {"min_str": 10, "damage_mult": 1.5},
            "Сокрушительный удар": {"min_str": 15, "damage_mult": 2.0, "stun_chance": 0.3},
            "Вихрь клинков": {"min_str": 20, "hits": 3, "damage_mult": 0.7}
        }
    },
    "dagger": {
        "name": "Кинжал",
        "damage": 5, 
        "base_skill": "Быстрая атака",
        "stat": "agility",
        "skills": {
            "Скоростной удар": {"min_agi": 10, "hits": 2},
            "Смертельный укол": {"min_agi": 15, "crit_chance": 0.5, "crit_mult": 2.0},
            "Теневой клинок": {"min_agi": 20, "dodge_chance": 0.5, "damage_mult": 1.5}
        }
    },
    "mace": {
        "name": "Булава",
        "damage": 10, 
        "base_skill": "Оглушение",
        "stat": "strength",
        "skills": {
            "Раздробление": {"min_str": 10, "armor_pen": 0.5},
            "Землетрясение": {"min_str": 15, "aoe": True, "damage_mult": 1.2},
            "Удар грома": {"min_str": 20, "stun_chance": 0.4, "damage_mult": 1.8}
        }
    },
    "bow": {
        "name": "Лук",
        "damage": 7,
        "base_skill": "Точный выстрел",
        "stat": "accuracy",
        "skills": {
            "Двойной выстрел": {"min_acc": 10, "hits": 2},
            "Снайперский выстрел": {"min_acc": 15, "crit_chance": 0.6, "damage_mult": 2.5},
            "Град стрел": {"min_acc": 20, "hits": 5, "damage_mult": 0.6}
        }
    },
    "axe": {
        "name": "Топор",
        "damage": 12,
        "base_skill": "Мощный удар",
        "stat": "strength",
        "skills": {
            "Раскол": {"min_str": 10, "damage_mult": 1.8},
            "Берсерк": {"min_str": 15, "damage_mult": 2.0, "self_damage": 0.1},
            "Вихрь топора": {"min_str": 20, "hits": 2, "damage_mult": 1.2}
        }
    },
    "spear": {
        "name": "Копье",
        "damage": 9,
        "base_skill": "Точечный удар",
        "stat": "agility",
        "skills": {
            "Пробивание": {"min_agi": 10, "armor_pen": 0.7},
            "Скоростной укол": {"min_agi": 15, "hits": 3},
            "Копье судьбы": {"min_agi": 20, "crit_chance": 0.4, "crit_mult": 3.0}
        }
    },
    "hammer": {
        "name": "Молот",
        "damage": 14,
        "base_skill": "Сокрушающий удар",
        "stat": "strength",
        "skills": {
            "Разрушитель": {"min_str": 12, "damage_mult": 1.8, "armor_pen": 0.6},
            "Удар молота": {"min_str": 18, "stun_chance": 0.5, "damage_mult": 2.0},
            "Земной разлом": {"min_str": 25, "aoe": True, "damage_mult": 1.5}
        }
    },
    "crossbow": {
        "name": "Арбалет",
        "damage": 10,
        "base_skill": "Тяжелый выстрел",
        "stat": "accuracy",
        "skills": {
            "Прострел": {"min_acc": 12, "armor_pen": 0.8},
            "Шквал болтов": {"min_acc": 18, "hits": 4, "damage_mult": 0.7},
            "Смертельный болт": {"min_acc": 24, "crit_chance": 0.7, "crit_mult": 3.0}
        }
    }
}

# Уникальные этажи
FLOOR_DESCRIPTIONS = {
    1: "🌲 *Лес Гоблинов* 🌲\nПервый этаж Башни, покрытый густым лесом. Здесь обитают гоблины и другие мелкие твари.",
    2: "🏔️ *Оркские Горы* 🏔️\nСкалистые горы, где господствуют орки. Опасные тропы и сильные ветра.",
    3: "🌋 *Вулканические Пещеры* 🌋\nРаскаленные пещеры с лавовыми потоками. Обитают огнедышащие тролли и саламандры.",
    4: "🏰 *Забытая Цитадель* 🏰\nДревняя крепость, полная ловушек и нежити. Стены помнят давно забытые войны.",
    5: "🌌 *Звездное Плато* 🌌\nТаинственное место под открытым небом, где ночью видны все созвездия. Обитают космические сущности.",
    6: "🧊 *Ледяные Пустоши* 🧊\nБескрайние ледяные поля, где холод может убить быстрее любого монстра.",
    7: "🌿 *Джунгли Забвения* 🌿\nГустые, почти непроходимые джунгли с гигантскими растениями и опасными хищниками.",
    8: "🏺 *Гробница Фараона* 🏺\nДревняя гробница, полная ловушек и проклятых сокровищ.",
    9: "⚡ *Грозовая Твердыня* ⚡\nПарящая в небе крепость, окруженная вечными грозами.",
    10: "💎 *Кристальные Пещеры* 💎\nМерцающие пещеры из живых кристаллов, искажающих реальность."
}

# Мобы по этажам
monsters_data = {
    1: [
        {"name": "Гоблин", "hp": 30, "damage": 5, "gold": (3, 10), "exp": 10},
        {"name": "Гоблин-разведчик", "hp": 25, "damage": 7, "gold": (5, 12), "exp": 12},
        {"name": "Гоблин-воин", "hp": 40, "damage": 9, "gold": (7, 15), "exp": 15}
    ],
    2: [
        {"name": "Орк", "hp": 50, "damage": 8, "gold": (5, 15), "exp": 20},
        {"name": "Орк-берсерк", "hp": 60, "damage": 12, "gold": (7, 18), "exp": 25},
        {"name": "Орк-шаман", "hp": 40, "damage": 15, "gold": (10, 25), "exp": 30, "skills": ["Силовой удар"]}
    ],
    3: [
        {"name": "Огненный тролль", "hp": 80, "damage": 12, "gold": (10, 20), "exp": 30, "fire_resist": True},
        {"name": "Лавовая саламандра", "hp": 70, "damage": 10, "gold": (12, 25), "exp": 35, "regen": 5},
        {"name": "Магма голем", "hp": 90, "damage": 18, "gold": (15, 30), "exp": 40}
    ],
    4: [
        {"name": "Скелет-воин", "hp": 60, "damage": 10, "gold": (10, 20), "exp": 40},
        {"name": "Призрак", "hp": 40, "damage": 15, "gold": (15, 30), "exp": 50, "dodge_chance": 0.3},
        {"name": "Лич", "hp": 100, "damage": 20, "gold": (20, 40), "exp": 70, "skills": ["Ледяная стрела"]}
    ],
    5: [
        {"name": "Звездный хищник", "hp": 100, "damage": 15, "gold": (20, 40), "exp": 70},
        {"name": "Космический слизень", "hp": 120, "damage": 10, "gold": (25, 50), "exp": 80, "regen": 10},
        {"name": "Ночной охотник", "hp": 90, "damage": 25, "gold": (30, 60), "exp": 90, "stealth": True}
    ],
    6: [
        {"name": "Ледяной элементаль", "hp": 120, "damage": 15, "gold": (30, 50), "exp": 90},
        {"name": "Йети", "hp": 150, "damage": 20, "gold": (40, 60), "exp": 100},
        {"name": "Морозный дракончик", "hp": 100, "damage": 25, "gold": (50, 80), "exp": 120}
    ],
    7: [
        {"name": "Ядовитый паук", "hp": 80, "damage": 20, "gold": (40, 60), "exp": 100, "poison": True},
        {"name": "Гигантская пиявка", "hp": 120, "damage": 15, "gold": (50, 70), "exp": 110, "lifesteal": 0.3},
        {"name": "Растение-людоед", "hp": 150, "damage": 25, "gold": (60, 90), "exp": 130, "root_chance": 0.4}
    ],
    8: [
        {"name": "Мумия", "hp": 100, "damage": 20, "gold": (50, 80), "exp": 120},
        {"name": "Скорпион-хранитель", "hp": 130, "damage": 25, "gold": (70, 100), "exp": 140},
        {"name": "Проклятый саркофаг", "hp": 200, "damage": 30, "gold": (100, 150), "exp": 160}
    ],
    9: [
        {"name": "Грозовой элементаль", "hp": 150, "damage": 25, "gold": (80, 120), "exp": 150},
        {"name": "Воздушный демон", "hp": 130, "damage": 30, "gold": (100, 150), "exp": 170},
        {"name": "Повелитель молний", "hp": 180, "damage": 35, "gold": (120, 180), "exp": 190}
    ],
    10: [
        {"name": "Кристальный голем", "hp": 200, "damage": 30, "gold": (150, 200), "exp": 200},
        {"name": "Призрачный кристалл", "hp": 150, "damage": 40, "gold": (180, 250), "exp": 220},
        {"name": "Исказитель реальности", "hp": 250, "damage": 50, "gold": (200, 300), "exp": 250}
    ]
}

# Боссы по этажам
bosses_data = {
    1: {
        "name": "Король Гоблинов",
        "hp": 500,
        "max_hp": 500,
        "damage": 20,
        "gold": (100, 200),
        "exp": 100,
        "skills": ["Сокрушительный удар", "Зов орды"],
        "description": "Мощный противник, окруженный свитой из гоблинов. Атакует размашистыми ударами.",
        "min_level": 5
    },
    2: {
        "name": "Вождь Орд",
        "hp": 1000,
        "max_hp": 1000,
        "damage": 30,
        "gold": (200, 300),
        "exp": 200,
        "skills": ["Землетрясение", "Ярость берсерка"],
        "description": "Гигантский орк, вооруженный двуручным топором. Вызывает подкрепления.",
        "min_level": 10
    },
    3: {
        "name": "Магма Повелитель",
        "hp": 2000,
        "max_hp": 2000,
        "damage": 40,
        "gold": (300, 500),
        "exp": 300,
        "skills": ["Огненный шторм", "Лавовая броня"],
        "description": "Монстр из чистой магмы, восстанавливающий здоровье в лаве.",
        "min_level": 15
    },
    4: {
        "name": "Король Мертвых",
        "hp": 3000,
        "max_hp": 3000,
        "damage": 50,
        "gold": (500, 700),
        "exp": 500,
        "skills": ["Проклятие", "Воскрешение нежити"],
        "description": "Древний правитель, восставший из мертвых. Управляет армией нежити.",
        "min_level": 20
    },
    5: {
        "name": "Звездный Дракон",
        "hp": 5000,
        "max_hp": 5000,
        "damage": 70,
        "gold": (800, 1200),
        "exp": 800,
        "skills": ["Космический луч", "Гравитационная аномалия"],
        "description": "Древний дракон, пришедший из глубин космоса. Контролирует звездную энергию.",
        "min_level": 25
    },
    6: {
        "name": "Ледяная Королева",
        "hp": 7000,
        "max_hp": 7000,
        "damage": 90,
        "gold": (1200, 1800),
        "exp": 1200,
        "skills": ["Абсолютный ноль", "Ледяная тюрьма"],
        "description": "Владычица холода, способная заморозить все вокруг одним движением руки.",
        "min_level": 30
    },
    7: {
        "name": "Повелитель Джунглей",
        "hp": 9000,
        "max_hp": 9000,
        "damage": 110,
        "gold": (1800, 2500),
        "exp": 1800,
        "skills": ["Ядовитый туман", "Призыв хищников"],
        "description": "Древний дух джунглей, контролирующий всю флору и фауну.",
        "min_level": 35
    },
    8: {
        "name": "Фараон Бессмертный",
        "hp": 12000,
        "max_hp": 12000,
        "damage": 140,
        "gold": (2500, 3500),
        "exp": 2500,
        "skills": ["Песчаный шторм", "Проклятие фараона"],
        "description": "Древний правитель, обретший бессмертие через темные ритуалы.",
        "min_level": 40
    },
    9: {
        "name": "Повелитель Гроз",
        "hp": 15000,
        "max_hp": 15000,
        "damage": 170,
        "gold": (3500, 5000),
        "exp": 3500,
        "skills": ["Удар молнии", "Грозовой фронт"],
        "description": "Божество штормов, способное вызывать разрушительные ураганы.",
        "min_level": 45
    },
    10: {
        "name": "Хранитель Реальности",
        "hp": 20000,
        "max_hp": 20000,
        "damage": 200,
        "gold": (5000, 8000),
        "exp": 5000,
        "skills": ["Искажение пространства", "Временной разрыв"],
        "description": "Последний страж Башни, контролирующий саму ткань реальности.",
        "min_level": 50
    }
}

# Локации для исследования
exploration_locations = {
    1: [
        {"name": "Гоблинский лагерь", "description": "Грязные палатки и костры. Здесь полно гоблинов!", "gold": (5, 15), "exp": 10},
        {"name": "Заброшенная шахта", "description": "Темные туннели, полные опасностей и... возможно, сокровищ?", "gold": (10, 20), "exp": 15},
        {"name": "Таинственный алтарь", "description": "Древние руны светятся слабым светом. Чувствуется магия в воздухе.", "gold": (15, 25), "exp": 20, "special": "skill_scroll"}
    ],
    2: [
        {"name": "Оркская крепость", "description": "Грубые укрепления из дерева и камня. Орки ведут постоянные войны.", "gold": (15, 25), "exp": 20},
        {"name": "Проклятый лес", "description": "Деревья шепчут проклятия на забытом языке. Лучше не задерживаться здесь надолго.", "gold": (20, 30), "exp": 25},
        {"name": "Руины древнего храма", "description": "Когда-то здесь поклонялись забытым богам. Теперь здесь обитают только тени.", "gold": (25, 40), "exp": 30, "special": "ancient_artifact"}
    ],
    3: [
        {"name": "Лавовое озеро", "description": "Огромное озеро кипящей лавы. Здесь можно найти редкие минералы.", "gold": (30, 50), "exp": 40},
        {"name": "Огненные пещеры", "description": "Пещеры, наполненные вечным пламенем. Только самые стойкие могут здесь выжить.", "gold": (40, 60), "exp": 50},
        {"name": "Кузница Вулкана", "description": "Древняя кузница, где когда-то ковали легендарное оружие.", "gold": (50, 80), "exp": 60, "special": "weapon_blueprint"}
    ],
    4: [
        {"name": "Тронный зал", "description": "Величественный зал, где когда-то восседали короли. Теперь здесь правят нежить.", "gold": (50, 80), "exp": 70},
        {"name": "Королевская библиотека", "description": "Древние фолианты, хранящие забытые знания и опасные секреты.", "gold": (60, 100), "exp": 80},
        {"name": "Подземные катакомбы", "description": "Лабиринт туннелей, наполненный ловушками и сокровищами.", "gold": (70, 120), "exp": 90, "special": "ancient_tome"}
    ],
    5: [
        {"name": "Обсерватория", "description": "Башня для наблюдения за звездами, сохранившая древние астрономические инструменты.", "gold": (80, 120), "exp": 100},
        {"name": "Сад Лунного Света", "description": "Волшебный сад, где растения светятся в темноте. Здесь можно найти редкие травы.", "gold": (100, 150), "exp": 120},
        {"name": "Портал Звезд", "description": "Древний портал, ведущий к другим мирам. Излучает странную энергию.", "gold": (120, 180), "exp": 150, "special": "star_shard"}
    ]
}

# Предметы магазина
shop_items = {
    "health_potion": {"price": 50, "effect": 50, "description": "💉 Восстанавливает 50 HP"},
    "weapon_upgrade": {"price": 200, "effect": "level+1", "description": "⚡ Улучшает текущее оружие на 1 уровень"},
    "armor_upgrade": {"price": 150, "effect": "defense+5", "description": "🛡️ +5 к защите"},
    "elixir_strength": {"price": 300, "effect": "str+3", "description": "💪 +3 к силе на 1 час"},
    "elixir_agility": {"price": 300, "effect": "agi+3", "description": "🏃 +3 к ловкости на 1 час"},
    "elixir_vitality": {"price": 300, "effect": "vit+3", "description": "❤️ +3 к живучести на 1 час"},
    "elixir_luck": {"price": 300, "effect": "luck+3", "description": "🍀 +3 к удаче на 1 час"},
    "boss_key": {"price": 1000, "effect": "access", "description": "🔑 Ключ для вызова босса текущего этажа"}
}

# Система талантов
talent_trees = {
    "sword": [
        {"id": "sword1", "name": "Острота клинка", "cost": 1, "effect": "damage+5%"},
        {"id": "sword2", "name": "Фехтовальщик", "cost": 2, "effect": "crit_chance+3%"},
        {"id": "sword3", "name": "Рыцарская честь", "cost": 3, "effect": "defense+10%"},
        {"id": "sword4", "name": "Смертельный вихрь", "cost": 5, "effect": "unlock_skill"}
    ],
    "dagger": [
        {"id": "dagger1", "name": "Теневой удар", "cost": 1, "effect": "dodge+5%"},
        {"id": "dagger2", "name": "Ядовитое лезвие", "cost": 2, "effect": "poison_chance+20%"},
        {"id": "dagger3", "name": "Ассасин", "cost": 3, "effect": "backstab_damage+30%"},
        {"id": "dagger4", "name": "Смертельный танец", "cost": 5, "effect": "unlock_skill"}
    ],
    "mace": [
        {"id": "mace1", "name": "Сокрушитель", "cost": 1, "effect": "stun_chance+10%"},
        {"id": "mace2", "name": "Бронебойный удар", "cost": 2, "effect": "armor_pen+20%"},
        {"id": "mace3", "name": "Землетрясение", "cost": 3, "effect": "aoe_damage+15%"},
        {"id": "mace4", "name": "Молот богов", "cost": 5, "effect": "unlock_skill"}
    ],
    "bow": [
        {"id": "bow1", "name": "Меткий стрелок", "cost": 1, "effect": "accuracy+10%"},
        {"id": "bow2", "name": "Скорострельность", "cost": 2, "effect": "attack_speed+20%"},
        {"id": "bow3", "name": "Смертельный выстрел", "cost": 3, "effect": "crit_damage+30%"},
        {"id": "bow4", "name": "Дождь стрел", "cost": 5, "effect": "unlock_skill"}
    ],
    "axe": [
        {"id": "axe1", "name": "Кровавая ярость", "cost": 1, "effect": "damage+8%"},
        {"id": "axe2", "name": "Двойной удар", "cost": 2, "effect": "double_hit_chance+15%"},
        {"id": "axe3", "name": "Берсерк", "cost": 3, "effect": "damage+20%_when_hp_low"},
        {"id": "axe4", "name": "Вихрь разрушения", "cost": 5, "effect": "unlock_skill"}
    ],
    "spear": [
        {"id": "spear1", "name": "Дальнобойность", "cost": 1, "effect": "range+1"},
        {"id": "spear2", "name": "Пробивающий удар", "cost": 2, "effect": "armor_pen+25%"},
        {"id": "spear3", "name": "Контратака", "cost": 3, "effect": "counter_chance+30%"},
        {"id": "spear4", "name": "Удар дракона", "cost": 5, "effect": "unlock_skill"}
    ],
    "hammer": [
        {"id": "hammer1", "name": "Сокрушительная сила", "cost": 1, "effect": "damage+10%"},
        {"id": "hammer2", "name": "Шоковая волна", "cost": 2, "effect": "stun_chance+15%"},
        {"id": "hammer3", "name": "Разрушитель укреплений", "cost": 3, "effect": "building_damage+50%"},
        {"id": "hammer4", "name": "Апокалипсис", "cost": 5, "effect": "unlock_skill"}
    ],
    "crossbow": [
        {"id": "crossbow1", "name": "Тяжелый болт", "cost": 1, "effect": "damage+12%"},
        {"id": "crossbow2", "name": "Скорость перезарядки", "cost": 2, "effect": "reload_speed+25%"},
        {"id": "crossbow3", "name": "Бронебойный болт", "cost": 3, "effect": "armor_pen+30%"},
        {"id": "crossbow4", "name": "Смертельный выстрел", "cost": 5, "effect": "unlock_skill"}
    ]
}

# Эпические боссы для рейдов
epic_bosses = {
    "ancient_dragon": {
        "name": "Древний Дракон",
        "hp": 50000,
        "damage": 500,
        "min_players": 5,
        "rewards": {
            "gold": (5000, 10000),
            "items": ["dragon_scale", "ancient_artifact"],
            "titles": ["Победитель Драконов"]
        }
    },
    "titan": {
        "name": "Титан Пустоты",
        "hp": 75000,
        "damage": 700,
        "min_players": 8,
        "rewards": {
            "gold": (10000, 15000),
            "items": ["titan_heart", "void_crystal"],
            "titles": ["Покоритель Титанов"]
        }
    },
    "celestial_being": {
        "name": "Небесный Страж",
        "hp": 100000,
        "damage": 1000,
        "min_players": 10,
        "rewards": {
            "gold": (15000, 25000),
            "items": ["celestial_essence", "divine_shard"],
            "titles": ["Небесный Завоеватель"]
        }
    }
}