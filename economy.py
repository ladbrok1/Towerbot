import logging
import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum, auto
from database import Database

logger = logging.getLogger(__name__)

class CurrencyType(Enum):
    GOLD = auto()
    SILVER = auto()
    COPPER = auto()
    HONOR = auto()
    TOKENS = auto()
    GUILD_COINS = auto()

class TransactionType(Enum):
    PLAYER_TRADE = auto()
    SHOP_PURCHASE = auto()
    AUCTION = auto()
    QUEST_REWARD = auto()
    MOB_DROP = auto()
    CRAFTING = auto()
    GUILD_DEPOSIT = auto()

@dataclass
class EconomicEvent:
    id: str
    name: str
    description: str
    start_time: datetime
    end_time: datetime
    modifiers: Dict[str, float]  # {"gold_drop": 1.5, "shop_prices": 0.8}

@dataclass
class PlayerTransaction:
    player_id: int
    amount: int
    currency: CurrencyType
    transaction_type: TransactionType
    timestamp: datetime
    details: Optional[Dict] = None

class EconomyManager:
    def __init__(self, db: Database):
        self.db = db
        self.exchange_rates = {
            (CurrencyType.GOLD, CurrencyType.SILVER): 100,
            (CurrencyType.SILVER, CurrencyType.COPPER): 100,
            (CurrencyType.GOLD, CurrencyType.COPPER): 10000
        }
        self.active_events: List[EconomicEvent] = []
        self.price_index: Dict[str, float] = {}  # Товары и их базовые цены
        self._initialize_db()
        self._load_economic_events()

    def _initialize_db(self):
        """Создать необходимые таблицы в БД"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_balances (
                    player_id INTEGER PRIMARY KEY,
                    gold INTEGER DEFAULT 0,
                    silver INTEGER DEFAULT 0,
                    copper INTEGER DEFAULT 0,
                    honor INTEGER DEFAULT 0,
                    tokens INTEGER DEFAULT 0,
                    guild_coins INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS economic_transactions (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    amount INTEGER,
                    currency TEXT,
                    transaction_type TEXT,
                    timestamp TEXT,
                    details TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS economic_events (
                    event_id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    modifiers TEXT
                )
            """)
            conn.commit()

    def _load_economic_events(self):
        """Загрузить активные экономические события из БД"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_id, name, description, start_time, end_time, modifiers
                FROM economic_events
                WHERE end_time > datetime('now')
            """)
            
            for row in cursor.fetchall():
                event_id, name, description, start_time, end_time, modifiers = row
                self.active_events.append(EconomicEvent(
                    id=event_id,
                    name=name,
                    description=description,
                    start_time=datetime.fromisoformat(start_time),
                    end_time=datetime.fromisoformat(end_time),
                    modifiers=json.loads(modifiers)
                ))

    async def get_balance(self, player_id: int, currency: CurrencyType) -> int:
        """Получить баланс игрока в указанной валюте"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT {currency.name.lower()} 
                FROM player_balances 
                WHERE player_id = ?
            """, (player_id,))
            result = cursor.fetchone()
            return result[0] if result else 0

    async def update_balance(
        self,
        player_id: int,
        amount: int,
        currency: CurrencyType,
        transaction_type: TransactionType,
        details: Optional[Dict] = None
    ) -> bool:
        """Обновить баланс игрока с записью транзакции"""
        if amount == 0:
            return True

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Проверить существование записи
            cursor.execute("SELECT 1 FROM player_balances WHERE player_id = ?", (player_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO player_balances (player_id) VALUES (?)", (player_id,))

            # Обновить баланс
            cursor.execute(f"""
                UPDATE player_balances 
                SET {currency.name.lower()} = {currency.name.lower()} + ? 
                WHERE player_id = ?
            """, (amount, player_id))

            # Записать транзакцию
            cursor.execute("""
                INSERT INTO economic_transactions 
                (player_id, amount, currency, transaction_type, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                player_id,
                amount,
                currency.name,
                transaction_type.name,
                datetime.now().isoformat(),
                json.dumps(details) if details else None
            ))

            conn.commit()
            return True

    async def transfer_currency(
        self,
        from_player_id: int,
        to_player_id: int,
        amount: int,
        currency: CurrencyType,
        fee_percent: float = 0.0
    ) -> bool:
        """Перевести валюту между игроками с комиссией"""
        if amount <= 0:
            return False

        # Проверить баланс отправителя
        sender_balance = await self.get_balance(from_player_id, currency)
        if sender_balance < amount:
            return False

        fee = int(amount * fee_percent)
        amount_to_receive = amount - fee

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Списать у отправителя
            cursor.execute(f"""
                UPDATE player_balances 
                SET {currency.name.lower()} = {currency.name.lower()} - ? 
                WHERE player_id = ?
            """, (amount, from_player_id))

            # Зачислить получателю
            cursor.execute(f"""
                INSERT OR IGNORE INTO player_balances (player_id) VALUES (?)
            """, (to_player_id,))
            cursor.execute(f"""
                UPDATE player_balances 
                SET {currency.name.lower()} = {currency.name.lower()} + ? 
                WHERE player_id = ?
            """, (amount_to_receive, to_player_id))

            # Записать транзакции
            transfer_details = {
                "from_player": from_player_id,
                "to_player": to_player_id,
                "fee": fee
            }

            cursor.execute("""
                INSERT INTO economic_transactions 
                (player_id, amount, currency, transaction_type, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                from_player_id,
                -amount,
                currency.name,
                TransactionType.PLAYER_TRADE.name,
                datetime.now().isoformat(),
                json.dumps(transfer_details)
            ))

            cursor.execute("""
                INSERT INTO economic_transactions 
                (player_id, amount, currency, transaction_type, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                to_player_id,
                amount_to_receive,
                currency.name,
                TransactionType.PLAYER_TRADE.name,
                datetime.now().isoformat(),
                json.dumps(transfer_details)
            ))

            if fee > 0:
                cursor.execute("""
                    INSERT INTO economic_transactions 
                    (player_id, amount, currency, transaction_type, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    None,  # Система получает комиссию
                    fee,
                    currency.name,
                    TransactionType.PLAYER_TRADE.name,
                    datetime.now().isoformat(),
                    json.dumps(transfer_details)
                ))

            conn.commit()
            return True

    async def convert_currency(
        self,
        player_id: int,
        from_currency: CurrencyType,
        to_currency: CurrencyType,
        amount: int,
        fee_percent: float = 0.05
    ) -> Optional[int]:
        """Конвертировать валюту по установленному курсу"""
        if from_currency == to_currency:
            return None

        rate = self.exchange_rates.get((from_currency, to_currency))
        if not rate:
            return None

        # Проверить баланс
        balance = await self.get_balance(player_id, from_currency)
        if balance < amount:
            return None

        fee = int(amount * fee_percent)
        amount_after_fee = amount - fee
        converted_amount = amount_after_fee * rate

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Списать исходную валюту
            cursor.execute(f"""
                UPDATE player_balances 
                SET {from_currency.name.lower()} = {from_currency.name.lower()} - ? 
                WHERE player_id = ?
            """, (amount, player_id))

            # Зачислить новую валюту
            cursor.execute(f"""
                UPDATE player_balances 
                SET {to_currency.name.lower()} = {to_currency.name.lower()} + ? 
                WHERE player_id = ?
            """, (converted_amount, player_id))

            # Записать транзакции
            conversion_details = {
                "from_currency": from_currency.name,
                "to_currency": to_currency.name,
                "rate": rate,
                "fee": fee
            }

            cursor.execute("""
                INSERT INTO economic_transactions 
                (player_id, amount, currency, transaction_type, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                player_id,
                -amount,
                from_currency.name,
                TransactionType.PLAYER_TRADE.name,
                datetime.now().isoformat(),
                json.dumps(conversion_details)
            ))

            cursor.execute("""
                INSERT INTO economic_transactions 
                (player_id, amount, currency, transaction_type, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                player_id,
                converted_amount,
                to_currency.name,
                TransactionType.PLAYER_TRADE.name,
                datetime.now().isoformat(),
                json.dumps(conversion_details)
            ))

            if fee > 0:
                cursor.execute("""
                    INSERT INTO economic_transactions 
                    (player_id, amount, currency, transaction_type, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    None,  # Система получает комиссию
                    fee,
                    from_currency.name,
                    TransactionType.PLAYER_TRADE.name,
                    datetime.now().isoformat(),
                    json.dumps(conversion_details)
                ))

            conn.commit()
            return converted_amount

    async def get_transaction_history(
        self,
        player_id: int,
        limit: int = 10,
        currency: Optional[CurrencyType] = None
    ) -> List[PlayerTransaction]:
        """Получить историю транзакций игрока"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT amount, currency, transaction_type, timestamp, details
                FROM economic_transactions
                WHERE player_id = ?
            """
            params = [player_id]
            
            if currency:
                query += " AND currency = ?"
                params.append(currency.name)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            return [
                PlayerTransaction(
                    player_id=player_id,
                    amount=row[0],
                    currency=CurrencyType[row[1]],
                    transaction_type=TransactionType[row[2]],
                    timestamp=datetime.fromisoformat(row[3]),
                    details=json.loads(row[4]) if row[4] else None
                ) for row in cursor.fetchall()
            ]

    async def add_economic_event(self, event: EconomicEvent) -> bool:
        """Добавить экономическое событие"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO economic_events 
                (event_id, name, description, start_time, end_time, modifiers)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event.id,
                event.name,
                event.description,
                event.start_time.isoformat(),
                event.end_time.isoformat(),
                json.dumps(event.modifiers)
            ))
            conn.commit()
        
        self.active_events.append(event)
        return True

    async def get_active_modifiers(self) -> Dict[str, float]:
        """Получить активные модификаторы экономики"""
        modifiers = {}
        now = datetime.now()
        
        for event in self.active_events:
            if event.start_time <= now <= event.end_time:
                for key, value in event.modifiers.items():
                    if key in modifiers:
                        modifiers[key] *= value
                    else:
                        modifiers[key] = value
        
        return modifiers

    async def calculate_item_price(
        self,
        base_price: int,
        item_type: str,
        player_level: Optional[int] = None
    ) -> int:
        """Рассчитать цену предмета с учетом всех модификаторов"""
        modifiers = await self.get_active_modifiers()
        price = base_price
        
        # Применить общие модификаторы цен
        if "shop_prices" in modifiers:
            price = int(price * modifiers["shop_prices"])
        
        # Модификаторы для типа предмета
        type_modifier_key = f"{item_type}_prices"
        if type_modifier_key in modifiers:
            price = int(price * modifiers[type_modifier_key])
        
        # Модификаторы для уровня игрока
        if player_level and "level_price_modifier" in modifiers:
            level_factor = 1 + (player_level / 100)
            price = int(price * level_factor * modifiers["level_price_modifier"])
        
        # Гарантированная минимальная цена
        return max(1, price)

    async def generate_inflation_report(self, days: int = 30) -> Dict[str, float]:
        """Сгенерировать отчет об инфляции за период"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получить средние цены за период
            cursor.execute("""
                SELECT AVG(amount) as avg_amount, currency
                FROM economic_transactions
                WHERE timestamp >= datetime('now', ?)
                AND transaction_type = 'SHOP_PURCHASE'
                GROUP BY currency
            """, (f"-{days} days",))
            
            current_prices = {row[1]: row[0] for row in cursor.fetchall()}
            
            # Получить средние цены за предыдущий период
            cursor.execute("""
                SELECT AVG(amount) as avg_amount, currency
                FROM economic_transactions
                WHERE timestamp BETWEEN datetime('now', ?) AND datetime('now', ?)
                AND transaction_type = 'SHOP_PURCHASE'
                GROUP BY currency
            """, (f"-{days*2} days", f"-{days} days"))
            
            previous_prices = {row[1]: row[0] for row in cursor.fetchall()}
            
            # Рассчитать инфляцию
            inflation = {}
            for currency, current_price in current_prices.items():
                previous_price = previous_prices.get(currency)
                if previous_price and previous_price > 0:
                    inflation[currency] = (current_price - previous_price) / previous_price * 100
            
            return inflation
