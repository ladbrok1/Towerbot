import logging
import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime, timedelta
from database import Database
from player import Player

logger = logging.getLogger(__name__)

class ItemType(Enum):
    WEAPON = auto()
    ARMOR = auto()
    CONSUMABLE = auto()
    MATERIAL = auto()
    QUEST = auto()
    SPECIAL = auto()

class CurrencyType(Enum):
    GOLD = auto()
    HONOR = auto()
    TOKENS = auto()
    GUILD_COINS = auto()

@dataclass
class ShopItem:
    id: str
    name: str
    type: ItemType
    price: int
    currency: CurrencyType
    stock: int
    max_per_player: int
    required_level: int
    required_rank: Optional[str] = None
    required_quest: Optional[str] = None
    discount: float = 1.0
    expires_at: Optional[datetime] = None

@dataclass
class PlayerPurchase:
    player_id: int
    item_id: str
    quantity: int
    last_purchased: datetime

class ShopManager:
    def __init__(self, db: Database, config_path: str = "shop_config.json"):
        self.db = db
        self.items: Dict[str, ShopItem] = {}
        self.player_purchases: Dict[int, Dict[str, PlayerPurchase]] = {}
        self.load_config(config_path)
        self.load_purchase_history()

    def load_config(self, config_path: str):
        """Загрузить конфигурацию магазина из файла"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for item_data in data['items']:
                    item = ShopItem(
                        id=item_data['id'],
                        name=item_data['name'],
                        type=ItemType[item_data['type']],
                        price=item_data['price'],
                        currency=CurrencyType[item_data['currency']],
                        stock=item_data.get('stock', -1),
                        max_per_player=item_data.get('max_per_player', -1),
                        required_level=item_data.get('required_level', 1),
                        required_rank=item_data.get('required_rank'),
                        required_quest=item_data.get('required_quest'),
                        discount=item_data.get('discount', 1.0),
                        expires_at=datetime.fromisoformat(item_data['expires_at']) if 'expires_at' in item_data else None
                    )
                    self.items[item.id] = item
                    
        except Exception as e:
            logger.error(f"Failed to load shop config: {e}")
            raise

    def load_purchase_history(self):
        """Загрузить историю покупок игроков из БД"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT player_id, item_id, quantity, last_purchased FROM shop_purchases")
            
            for row in cursor.fetchall():
                player_id, item_id, quantity, last_purchased = row
                
                if player_id not in self.player_purchases:
                    self.player_purchases[player_id] = {}
                    
                self.player_purchases[player_id][item_id] = PlayerPurchase(
                    player_id=player_id,
                    item_id=item_id,
                    quantity=quantity,
                    last_purchased=datetime.fromisoformat(last_purchased)
                )

    def save_purchase(self, player_id: int, item_id: str, quantity: int):
        """Сохранить информацию о покупке в БД"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Обновить или добавить запись
            cursor.execute("""
                INSERT OR REPLACE INTO shop_purchases 
                (player_id, item_id, quantity, last_purchased) 
                VALUES (?, ?, ?, ?)
            """, (
                player_id,
                item_id,
                quantity,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            
            # Обновить кеш
            if player_id not in self.player_purchases:
                self.player_purchases[player_id] = {}
                
            self.player_purchases[player_id][item_id] = PlayerPurchase(
                player_id=player_id,
                item_id=item_id,
                quantity=quantity,
                last_purchased=datetime.now()
            )

    def get_available_items(self, player: Player) -> List[ShopItem]:
        """Получить список доступных для игрока товаров"""
        available_items = []
        
        for item in self.items.values():
            # Проверить срок действия
            if item.expires_at and item.expires_at < datetime.now():
                continue
                
            # Проверить уровень
            if player.level < item.required_level:
                continue
                
            # Проверить ранги/квесты
            if item.required_rank and item.required_rank not in player.ranks:
                continue
                
            if item.required_quest and item.required_quest not in player.completed_quests:
                continue
                
            # Проверить остаток
            if item.stock == 0:
                continue
                
            available_items.append(item)
            
        return available_items

    def get_player_purchases(self, player_id: int, item_id: str = None) -> Union[PlayerPurchase, Dict[str, PlayerPurchase]]:
        """Получить историю покупок игрока"""
        if player_id not in self.player_purchases:
            return {} if item_id is None else None
            
        if item_id:
            return self.player_purchases[player_id].get(item_id)
            
        return self.player_purchases[player_id]

    def purchase_item(self, player: Player, item_id: str, quantity: int = 1) -> Dict:
        """Покупка товара игроком"""
        if item_id not in self.items:
            return {'success': False, 'message': 'Товар не найден'}
            
        item = self.items[item_id]
        
        # Проверить доступность
        if not self._check_availability(player, item, quantity):
            return {'success': False, 'message': 'Товар недоступен для покупки'}
            
        # Проверить валюту
        currency_balance = self._get_player_currency(player, item.currency)
        total_price = int(item.price * quantity * item.discount)
        
        if currency_balance < total_price:
            return {'success': False, 'message': 'Недостаточно средств'}
            
        # Проверить инвентарь
        if not player.has_inventory_space(quantity):
            return {'success': False, 'message': 'Недостаточно места в инвентаре'}
            
        # Выполнить покупку
        self._deduct_currency(player, item.currency, total_price)
        player.add_item_to_inventory(item_id, quantity)
        
        # Обновить остатки
        if item.stock > 0:
            item.stock -= quantity
            
        # Обновить историю покупок
        current_purchases = self.get_player_purchases(player.user_id, item_id)
        new_quantity = quantity + (current_purchases.quantity if current_purchases else 0)
        self.save_purchase(player.user_id, item_id, new_quantity)
        
        return {
            'success': True,
            'message': f'Успешно куплено {quantity} {item.name}',
            'remaining_balance': self._get_player_currency(player, item.currency),
            'remaining_stock': item.stock
        }

    def _check_availability(self, player: Player, item: ShopItem, quantity: int) -> bool:
        """Проверить доступность товара"""
        # Проверить срок действия
        if item.expires_at and item.expires_at < datetime.now():
            return False
            
        # Проверить уровень
        if player.level < item.required_level:
            return False
            
        # Проверить ранги/квесты
        if item.required_rank and item.required_rank not in player.ranks:
            return False
            
        if item.required_quest and item.required_quest not in player.completed_quests:
            return False
            
        # Проверить остаток
        if item.stock > 0 and quantity > item.stock:
            return False
            
        # Проверить лимит на игрока
        if item.max_per_player > 0:
            player_purchase = self.get_player_purchases(player.user_id, item.id)
            if player_purchase and player_purchase.quantity + quantity > item.max_per_player:
                return False
                
        return True

    def _get_player_currency(self, player: Player, currency: CurrencyType) -> int:
        """Получить баланс игрока в указанной валюте"""
        if currency == CurrencyType.GOLD:
            return player.gold
        elif currency == CurrencyType.HONOR:
            return player.honor
        elif currency == CurrencyType.TOKENS:
            return player.tokens
        elif currency == CurrencyType.GUILD_COINS:
            return player.guild_coins
        return 0

    def _deduct_currency(self, player: Player, currency: CurrencyType, amount: int):
        """Списать валюту с игрока"""
        if currency == CurrencyType.GOLD:
            player.gold -= amount
        elif currency == CurrencyType.HONOR:
            player.honor -= amount
        elif currency == CurrencyType.TOKENS:
            player.tokens -= amount
        elif currency == CurrencyType.GUILD_COINS:
            player.guild_coins -= amount

    def add_discount(self, item_id: str, discount: float, duration_hours: int = 24):
        """Добавить временную скидку на товар"""
        if item_id in self.items:
            self.items[item_id].discount = discount
            self.items[item_id].expires_at = datetime.now() + timedelta(hours=duration_hours)

    def restock_items(self):
        """Пополнить запасы товаров (вызывается по расписанию)"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_id, stock FROM shop_restock")
            
            for item_id, stock in cursor.fetchall():
                if item_id in self.items:
                    self.items[item_id].stock = stock

    def get_limited_offers(self) -> List[ShopItem]:
        """Получить список товаров с ограниченным предложением"""
        return [
            item for item in self.items.values()
            if item.stock > 0 or item.max_per_player > 0 or item.expires_at
        ]

    def get_daily_deals(self, player: Player) -> List[ShopItem]:
        """Получить ежедневные предложения для игрока"""
        today = datetime.now().date()
        seed = hash(f"{player.user_id}_{today}") % 1000
        
        # Выбрать 3 случайных товара с учетом уровня игрока
        eligible_items = [
            item for item in self.items.values()
            if player.level >= item.required_level and
               item.discount >= 1.0 and
               (not item.required_rank or item.required_rank in player.ranks)
        ]
        
        random.seed(seed)
        daily_items = random.sample(eligible_items, min(3, len(eligible_items)))
        
        # Применить скидку 20% на ежедневные товары
        for item in daily_items:
            item.discount = 0.8
            item.expires_at = datetime.now() + timedelta(hours=24)
            
        return daily_items
