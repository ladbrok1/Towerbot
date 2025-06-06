import random
import logging
from typing import Dict, Optional, List, Tuple
from player import Player
from database import Database
from combat import CombatSystem

logger = logging.getLogger(__name__)

class PvPManager:
    def __init__(self, db: Database, combat_system: CombatSystem):
        self.db = db
        self.combat_system = combat_system
        self.duels: Dict[int, Dict] = {}  # {chat_id: duel_data}
        self.arena_queues: Dict[str, List[int]] = {
            '1v1': [],
            '3v3': [],
            '5v5': []
        }
        self.pvp_zones = {
            'blood_arena': {'min_level': 30, 'max_players': 20},
            'wild_lands': {'min_level': 15, 'max_players': 50}
        }
        self.honor_rewards = {
            'win': 50,
            'loss': 10,
            'kill': 15
        }

    async def challenge_player(self, challenger: Player, target: Player) -> Dict:
        """Отправить вызов на дуэль другому игроку"""
        if challenger.user_id == target.user_id:
            return {'success': False, 'message': 'Нельзя вызвать самого себя!'}

        if challenger.level < 10 or target.level < 10:
            return {'success': False, 'message': 'Для PvP нужен как минимум 10 уровень'}

        if challenger.current_hp < challenger.max_hp * 0.5:
            return {'success': False, 'message': 'Ваше здоровье должно быть выше 50%'}

        duel_id = hash(f"{challenger.user_id}_{target.user_id}_{random.randint(1000, 9999)}")
        self.duels[duel_id] = {
            'challenger': challenger,
            'target': target,
            'status': 'pending',
            'timestamp': datetime.now(),
            'bet': 0
        }

        return {
            'success': True,
            'duel_id': duel_id,
            'message': f"{target.name}, вы получили вызов от {challenger.name}! Принять? /accept_duel_{duel_id}"
        }

    async def accept_duel(self, duel_id: int, accepted: bool) -> Dict:
        """Принять или отклонить вызов на дуэль"""
        duel = self.duels.get(duel_id)
        if not duel:
            return {'success': False, 'message': 'Вызов не найден или истек'}

        if not accepted:
            self.duels.pop(duel_id)
            return {'success': True, 'message': 'Вызов отклонен'}

        if duel['status'] != 'pending':
            return {'success': False, 'message': 'Этот вызов уже обработан'}

        challenger = duel['challenger']
        target = duel['target']

        # Проверка готовности игроков
        for player in [challenger, target]:
            if player.current_hp < player.max_hp * 0.3:
                self.duels.pop(duel_id)
                return {'success': False, 'message': f'{player.name} не готов к битве (HP < 30%)'}

        duel['status'] = 'active'
        battle_result = await self._start_duel(challenger, target)
        
        # Обновление статистики PvP
        await self._update_pvp_stats(challenger, target, battle_result['winner'])
        self.duels.pop(duel_id)
        
        return battle_result

    async def _start_duel(self, player1: Player, player2: Player) -> Dict:
        """Провести дуэль между двумя игроками"""
        logger.info(f"Starting duel between {player1.name} and {player2.name}")

        # Временные модификаторы для PvP
        pvp_modifiers = {
            'damage_reduction': 0.3,  # Уменьшение урона в PvP
            'cc_duration': 0.5       # Уменьшение длительности контроля
        }

        battle_log = []
        round_count = 0
        max_rounds = 20

        while player1.current_hp > 0 and player2.current_hp > 0 and round_count < max_rounds:
            round_count += 1
            round_log = f"🔴 Раунд {round_count}:"

            # Ход игрока 1
            attack_result = self.combat_system.pvp_attack(player1, player2, pvp_modifiers)
            round_log += f"\n{player1.name} наносит {attack_result['damage']} урона!"
            if attack_result.get('critical'):
                round_log += " Критический удар!"
            
            # Ход игрока 2
            if player2.current_hp > 0:
                attack_result = self.combat_system.pvp_attack(player2, player1, pvp_modifiers)
                round_log += f"\n{player2.name} наносит {attack_result['damage']} урона!"
                if attack_result.get('critical'):
                    round_log += " Критический удар!"

            battle_log.append(round_log)

        # Определение победителя
        if player1.current_hp <= 0:
            winner = player2
            loser = player1
        elif player2.current_hp <= 0:
            winner = player1
            loser = player2
        else:
            winner = None  # Ничья по таймауту

        # Восстановление здоровья после боя
        player1.current_hp = min(player1.current_hp, player1.max_hp * 0.3)
        player2.current_hp = min(player2.current_hp, player2.max_hp * 0.3)

        return {
            'winner': winner,
            'loser': loser,
            'is_draw': winner is None,
            'rounds': round_count,
            'battle_log': battle_log,
            'honor_gained': self.honor_rewards['win'] if winner else 0
        }

    async def join_arena_queue(self, player: Player, arena_type: str) -> Dict:
        """Войти в очередь на арену"""
        if arena_type not in self.arena_queues:
            return {'success': False, 'message': 'Неверный тип арены'}

        if player.user_id in self.arena_queues[arena_type]:
            return {'success': False, 'message': 'Вы уже в очереди'}

        self.arena_queues[arena_type].append(player.user_id)
        return {'success': True, 'message': f'Вы в очереди на {arena_type} арену'}

    async def leave_arena_queue(self, player: Player) -> Dict:
        """Покинуть очередь на арену"""
        for queue in self.arena_queues.values():
            if player.user_id in queue:
                queue.remove(player.user_id)
                return {'success': True, 'message': 'Вы покинули очередь'}
        return {'success': False, 'message': 'Вы не в очереди'}

    async def check_arena_matches(self) -> List[Dict]:
        """Проверить и создать матчи для арены"""
        formed_matches = []
        
        # Обработка 1v1 очереди
        while len(self.arena_queues['1v1']) >= 2:
            player1_id = self.arena_queues['1v1'].pop(0)
            player2_id = self.arena_queues['1v1'].pop(0)
            
            formed_matches.append({
                'type': '1v1',
                'team1': [player1_id],
                'team2': [player2_id]
            })

        # Обработка 3v3 очереди (упрощенная версия)
        if len(self.arena_queues['3v3']) >= 6:
            team1 = [self.arena_queues['3v3'].pop(0) for _ in range(3)]
            team2 = [self.arena_queues['3v3'].pop(0) for _ in range(3)]
            
            formed_matches.append({
                'type': '3v3',
                'team1': team1,
                'team2': team2
            })

        return formed_matches

    async def _update_pvp_stats(self, player1: Player, player2: Player, winner: Optional[Player]) -> None:
        """Обновить PvP статистику игроков"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            if winner:
                loser = player2 if winner.user_id == player1.user_id else player1
                
                # Обновление победителя
                cursor.execute(
                    "UPDATE pvp_stats SET wins = wins + 1, honor = honor + ? WHERE user_id = ?",
                    (self.honor_rewards['win'], winner.user_id)
                
                # Обновление проигравшего
                cursor.execute(
                    "UPDATE pvp_stats SET losses = losses + 1, honor = honor + ? WHERE user_id = ?",
                    (self.honor_rewards['loss'], loser.user_id))
            else:
                # Ничья
                for player in [player1, player2]:
                    cursor.execute(
                        "UPDATE pvp_stats SET draws = draws + 1 WHERE user_id = ?",
                        (player.user_id,))

            conn.commit()

    async def get_pvp_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Получить таблицу лидеров PvP"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, wins, losses, draws, honor 
                FROM pvp_stats 
                ORDER BY honor DESC 
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]

    async def handle_pvp_zone_combat(self, attacker: Player, defender: Player) -> Dict:
        """Обработка боя в PvP зоне"""
        if not self._can_attack(attacker, defender):
            return {'success': False, 'message': 'Вы не можете атаковать этого игрока'}

        combat_result = await self._start_duel(attacker, defender)
        
        # Дополнительные награды за убийство в PvP зоне
        if combat_result['winner']:
            combat_result['honor_gained'] += self.honor_rewards['kill']
            await self._update_pvp_stats(attacker, defender, combat_result['winner'])
        
        return combat_result

    def _can_attack(self, attacker: Player, defender: Player) -> bool:
        """Проверить, может ли игрок атаковать другого"""
        # Игрок не может атаковать себя
        if attacker.user_id == defender.user_id:
            return False
        
        # Проверка уровня (опционально)
        if abs(attacker.level - defender.level) > 10:
            return False
        
        # Проверка фракций/гильдий (можно добавить)
        return True

    async def reset_pvp_season(self):
        """Сбросить PvP сезон и выдать награды"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получить топ игроков
            top_players = await self.get_pvp_leaderboard(100)
            
            # Выдать сезонные награды
            for i, player in enumerate(top_players, start=1):
                rewards = self._calculate_season_rewards(i)
                cursor.execute(
                    "INSERT INTO seasonal_rewards (user_id, season, position, rewards) VALUES (?, ?, ?, ?)",
                    (player['user_id'], datetime.now().strftime("%Y-%m"), i, str(rewards))
            
            # Сбросить статистику
            cursor.execute("UPDATE pvp_stats SET wins = 0, losses = 0, draws = 0")
            conn.commit()

    def _calculate_season_rewards(self, position: int) -> Dict:
        """Рассчитать сезонные награды по позиции"""
        if position == 1:
            return {'title': 'Gladiator', 'gold': 5000, 'items': ['legendary_weapon']}
        elif position <= 3:
            return {'title': 'Champion', 'gold': 3000, 'items': ['epic_armor']}
        elif position <= 10:
            return {'title': 'Elite', 'gold': 1500, 'items': ['rare_mount']}
        elif position <= 50:
            return {'title': 'Veteran', 'gold': 800}
        else:
            return {'title': 'Participant', 'gold': 300}
