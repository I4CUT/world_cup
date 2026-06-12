"""
Модуль построения сетки плейофф (1/16 финала -> финал) для ЧМ-2026.

Сетка 1/16 финала фиксирована регламентом FIFA (Annex B/C) и состоит из:
- 8 матчей между конкретными 1-ми и 2-ми местами групп (фиксированные пары)
- 8 матчей "Победитель группы X vs Лучшая команда с 3-го места из набора групп {...}"

Поскольку набор групп, давших третьих мест, определяется только после
завершения группового этапа, для каждого из 8 "третьих мест"-слотов задан
список групп-кандидатов в порядке приоритета согласно официальному
расписанию (Match 74, 77, 79, 80, 81, 82, 85, 87 и т.п.).

Алгоритм распределения третьих мест:
1. Берём 8 квалифицировавшихся команд с 3-х мест и группы, из которых они вышли.
2. У каждого из 8 слотов (матчи 74, 77, 79, 80, 81, 82, 85, 87) есть список
   из 5 групп-кандидатов.
3. Нужно найти биекцию "слот -> команда" такую, что группа каждой команды
   входит в список кандидатов её слота (паросочетание в двудольном графе).
4. Среди всех валидных биекций предпочитаем ту, где более рейтинговые
   команды (с меньшим rank, т.е. 3-1 лучше, чем 3-8) попадают в матчи
   с более ранним номером (74 раньше 87) — это приближает реальную логику
   FIFA, согласно которой порядок матчей в расписании коррелирует с тем,
   какой "уровень" соперника достаётся той или иной третьей команде.

Реализовано через backtracking (полный поиск по 8 слотам с откатом),
что гарантирует нахождение корректного распределения для любой из 495
легальных комбинаций групп.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from group_stage import Tournament


# ---------------------------------------------------------------------------
# Фиксированная сетка 1/16 финала (Round of 32), матчи 73-88
# ---------------------------------------------------------------------------
#
# Формат записи участника:
#   ('1', 'A')        -> победитель группы A
#   ('2', 'A')        -> второе место группы A
#   ('3', [...])      -> лучшая команда с 3-го места из списка групп-кандидатов
#
# Порядок матчей соответствует официальной нумерации FIFA (73-88).

ROUND_OF_32_FIXTURES: List[Tuple[str, Tuple[str, object], Tuple[str, object]]] = [
    ('M73', ('2', 'A'), ('2', 'B')),
    ('M74', ('1', 'E'), ('3', ['A', 'B', 'C', 'D', 'F'])),
    ('M75', ('1', 'F'), ('2', 'C')),
    ('M76', ('1', 'C'), ('2', 'F')),
    ('M77', ('1', 'I'), ('3', ['C', 'D', 'F', 'G', 'H'])),
    ('M78', ('2', 'E'), ('2', 'I')),
    ('M79', ('1', 'A'), ('3', ['C', 'E', 'F', 'H', 'I'])),
    ('M80', ('1', 'L'), ('3', ['E', 'H', 'I', 'J', 'K'])),
    ('M81', ('1', 'D'), ('3', ['B', 'E', 'F', 'I', 'J'])),
    ('M82', ('1', 'G'), ('3', ['A', 'E', 'H', 'I', 'J'])),
    ('M83', ('2', 'K'), ('2', 'L')),
    ('M84', ('1', 'H'), ('2', 'J')),
    ('M85', ('1', 'B'), ('3', ['E', 'F', 'G', 'I', 'J'])),
    ('M86', ('1', 'J'), ('2', 'H')),
    ('M87', ('1', 'K'), ('3', ['D', 'E', 'I', 'J', 'L'])),
    ('M88', ('2', 'D'), ('2', 'G')),
]

# Порядок, в котором слоты "лучшая 3-я команда" заполняются жадным алгоритмом.
# Соответствует хронологии матчей в расписании FIFA.
THIRD_PLACE_SLOT_ORDER = ['M74', 'M77', 'M79', 'M80', 'M81', 'M82', 'M85', 'M87']


# ---------------------------------------------------------------------------
# Структура сетки плейофф
# ---------------------------------------------------------------------------

@dataclass
class BracketMatch:
    """Один матч сетки плейофф."""
    match_id: str
    round_name: str  # 'R32', 'R16', 'QF', 'SF', 'F', '3RD'
    team1: Optional[str] = None
    team2: Optional[str] = None
    winner: Optional[str] = None
    # Откуда придут команды (для построения связей между раундами)
    source1: Optional[str] = None  # match_id предыдущего раунда или None
    source2: Optional[str] = None

    def set_winner(self, team: str):
        if team not in (self.team1, self.team2):
            raise ValueError(f"Команда {team} не участвует в матче {self.match_id}")
        self.winner = team


class Bracket:
    """Полная сетка плейофф ЧМ-2026: R32 -> R16 -> QF -> SF -> F (+ матч за 3-е место)."""

    # Связи раундов: какие матчи R32 формируют какой матч R16 и т.д.
    R16_LINKS = [
        ('R16-1', 'M73', 'M75'),
        ('R16-2', 'M74', 'M77'),
        ('R16-3', 'M76', 'M78'),
        ('R16-4', 'M79', 'M80'),
        ('R16-5', 'M83', 'M84'),
        ('R16-6', 'M81', 'M82'),
        ('R16-7', 'M86', 'M88'),
        ('R16-8', 'M85', 'M87'),
    ]

    QF_LINKS = [
        ('QF-1', 'R16-1', 'R16-2'),
        ('QF-2', 'R16-3', 'R16-4'),
        ('QF-3', 'R16-5', 'R16-6'),
        ('QF-4', 'R16-7', 'R16-8'),
    ]

    SF_LINKS = [
        ('SF-1', 'QF-1', 'QF-2'),
        ('SF-2', 'QF-3', 'QF-4'),
    ]

    FINAL_LINK = ('FINAL', 'SF-1', 'SF-2')
    THIRD_PLACE_LINK = ('3RD', 'SF-1', 'SF-2')  # проигравшие полуфиналов

    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.matches: Dict[str, BracketMatch] = {}
        self._build_r32()
        self._build_later_rounds()

    # ------------------------------------------------------------------
    # Построение раунда 1/16 финала
    # ------------------------------------------------------------------
    def _build_r32(self):
        qualified = self.tournament.qualified_teams()

        # Извлекаем 8 лучших третьих мест с информацией об их группах
        third_place_pool: List[Tuple[str, str]] = []  # (команда, группа)
        for rank in range(1, 9):
            team = qualified.get(f'3-{rank}')
            grp = qualified.get(f'3-{rank}-group')
            if team is not None:
                third_place_pool.append((team, grp))

        # Распределение третьих мест по слотам через backtracking:
        # ищем биекцию slot_id -> (команда, группа), где группа команды
        # входит в список кандидатов слота.
        slot_candidates: Dict[str, List[str]] = {}
        for mid, t1, t2 in ROUND_OF_32_FIXTURES:
            for kind, cand in (t1, t2):
                if kind == '3':
                    slot_candidates[mid] = cand

        third_place_assignment: Dict[str, Optional[str]] = self._assign_third_places(
            third_place_pool, slot_candidates
        )

        # Создаём матчи R32
        for match_id, t1, t2 in ROUND_OF_32_FIXTURES:
            team1 = self._resolve_slot(t1, qualified, third_place_assignment, match_id)
            team2 = self._resolve_slot(t2, qualified, third_place_assignment, match_id)
            self.matches[match_id] = BracketMatch(
                match_id=match_id,
                round_name='R32',
                team1=team1,
                team2=team2,
            )

    @staticmethod
    def _assign_third_places(third_place_pool: List[Tuple[str, str]],
                              slot_candidates: Dict[str, List[str]]) -> Dict[str, Optional[str]]:
        """
        Находит распределение slot_id -> команда (биекция) через backtracking,
        такое что группа команды входит в список кандидатов её слота.

        third_place_pool: список (команда, группа), отсортированный по рейтингу
                          (лучшая команда первая).
        slot_candidates: slot_id -> список допустимых групп.

        Слоты обходятся в порядке THIRD_PLACE_SLOT_ORDER, команды — в порядке
        рейтинга, что приближает реальную логику FIFA (сильнейшие третьи места
        попадают в более ранние/благоприятные слоты при наличии выбора).
        """
        slots = THIRD_PLACE_SLOT_ORDER
        teams = third_place_pool  # [(team, group), ...]

        assignment: Dict[str, Optional[str]] = {}
        used_teams: set = set()

        def backtrack(slot_idx: int) -> bool:
            if slot_idx == len(slots):
                return True
            slot_id = slots[slot_idx]
            allowed_groups = slot_candidates[slot_id]
            for team, grp in teams:
                if team in used_teams:
                    continue
                if grp in allowed_groups:
                    assignment[slot_id] = team
                    used_teams.add(team)
                    if backtrack(slot_idx + 1):
                        return True
                    used_teams.remove(team)
                    del assignment[slot_id]
            return False

        success = backtrack(0)
        if not success:
            for slot_id in slots:
                assignment.setdefault(slot_id, None)

        return assignment

    @staticmethod
    def _resolve_slot(slot, qualified: Dict[str, str],
                       third_place_assignment: Dict[str, str],
                       match_id: str) -> Optional[str]:
        kind, value = slot
        if kind == '1':
            return qualified.get(f'1{value}')
        elif kind == '2':
            return qualified.get(f'2{value}')
        elif kind == '3':
            return third_place_assignment.get(match_id)
        raise ValueError(f"Неизвестный тип слота: {kind}")

    # ------------------------------------------------------------------
    # Построение R16, QF, SF, Финала и матча за 3-е место
    # ------------------------------------------------------------------
    def _build_later_rounds(self):
        for match_id, src1, src2 in self.R16_LINKS:
            self.matches[match_id] = BracketMatch(
                match_id=match_id, round_name='R16',
                source1=src1, source2=src2,
            )
        for match_id, src1, src2 in self.QF_LINKS:
            self.matches[match_id] = BracketMatch(
                match_id=match_id, round_name='QF',
                source1=src1, source2=src2,
            )
        for match_id, src1, src2 in self.SF_LINKS:
            self.matches[match_id] = BracketMatch(
                match_id=match_id, round_name='SF',
                source1=src1, source2=src2,
            )
        fid, s1, s2 = self.FINAL_LINK
        self.matches[fid] = BracketMatch(match_id=fid, round_name='F', source1=s1, source2=s2)

        tid, s1, s2 = self.THIRD_PLACE_LINK
        self.matches[tid] = BracketMatch(match_id=tid, round_name='3RD', source1=s1, source2=s2)

    # ------------------------------------------------------------------
    # Установка победителя и продвижение по сетке
    # ------------------------------------------------------------------
    def set_winner(self, match_id: str, winner: str):
        """Устанавливает победителя матча и обновляет команды в следующих раундах."""
        m = self.matches[match_id]
        m.set_winner(winner)
        self._propagate()

    def _propagate(self):
        """Пересчитывает team1/team2 во всех матчах, зависящих от source1/source2."""
        # Несколько проходов, т.к. зависимости могут быть многоуровневыми
        for _ in range(4):
            for m in self.matches.values():
                if m.source1:
                    src = self.matches[m.source1]
                    if m.round_name == '3RD':
                        # Матч за 3-е место — проигравшие полуфиналов
                        m.team1 = self._loser(src)
                    else:
                        m.team1 = src.winner
                if m.source2:
                    src = self.matches[m.source2]
                    if m.round_name == '3RD':
                        m.team2 = self._loser(src)
                    else:
                        m.team2 = src.winner

    @staticmethod
    def _loser(m: BracketMatch) -> Optional[str]:
        if m.winner is None:
            return None
        return m.team2 if m.winner == m.team1 else m.team1

    # ------------------------------------------------------------------
    # Утилиты для отображения
    # ------------------------------------------------------------------
    def get_match(self, match_id: str) -> BracketMatch:
        return self.matches[match_id]

    def get_round(self, round_name: str) -> List[BracketMatch]:
        order = ['R32', 'R16', 'QF', 'SF', 'F', '3RD']
        if round_name not in order:
            raise ValueError(f"Неизвестный раунд: {round_name}")
        return [m for m in self.matches.values() if m.round_name == round_name]

    def champion(self) -> Optional[str]:
        return self.matches['FINAL'].winner

    def is_ready(self, match_id: str) -> bool:
        """Можно ли уже выбирать победителя этого матча (обе команды известны)?"""
        m = self.matches[match_id]
        return m.team1 is not None and m.team2 is not None


if __name__ == '__main__':
    # Демонстрация на тех же демо-данных, что в group_stage.py
    demo_groups = {
        chr(ord('A') + i): [f'{chr(ord("A") + i)}{j}' for j in range(1, 5)]
        for i in range(12)
    }
    t = Tournament(demo_groups)

    # Заполняем все группы одинаковым "сценарием" для теста:
    # team1 побеждает всех, team2 второй, team3/team4 борются за третье место
    import itertools
    for name, g in t.groups.items():
        results = {
            (0, 1): (2, 0), (0, 2): (1, 0), (0, 3): (3, 0),
            (1, 2): (1, 0), (1, 3): (2, 0), (2, 3): (1, 1),
        }
        for (i, j), (s1, s2) in results.items():
            g.set_result(g.teams[i], g.teams[j], s1, s2)

    qualified = t.qualified_teams()
    print("Квалифицировались:")
    for k, v in qualified.items():
        print(f"  {k}: {v}")

    bracket = Bracket(t)
    print("\nСетка 1/16 финала:")
    for m in bracket.get_round('R32'):
        print(f"  {m.match_id}: {m.team1} vs {m.team2}")

    # Тест продвижения: первые команды побеждают везде
    print("\nПродвижение (team1 побеждает во всех матчах):")
    for round_name in ['R32', 'R16', 'QF', 'SF']:
        for m in bracket.get_round(round_name):
            if bracket.is_ready(m.match_id):
                bracket.set_winner(m.match_id, m.team1)

    final = bracket.get_match('FINAL')
    third = bracket.get_match('3RD')
    print(f"  Финал: {final.team1} vs {final.team2}")
    if bracket.is_ready('FINAL'):
        bracket.set_winner('FINAL', final.team1)
        bracket.set_winner('3RD', third.team1)
    print(f"  Чемпион: {bracket.champion()}")
    print(f"  Матч за 3-е место: {third.team1} vs {third.team2}")
