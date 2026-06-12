"""
Модуль логики группового этапа ЧМ-2026.

Содержит:
- структуру матчей внутри группы (round robin для 4 команд)
- расчёт таблицы (очки, голы, разница)
- сортировку с тай-брейками по регламенту FIFA
- вычисление 8 лучших команд, занявших 3-и места (для выхода в плейофф)
"""

from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Tuple


@dataclass
class Match:
    """Один матч группового этапа."""
    team1: str
    team2: str
    score1: Optional[int] = None
    score2: Optional[int] = None

    @property
    def played(self) -> bool:
        return self.score1 is not None and self.score2 is not None

    def result_for(self, team: str) -> Optional[str]:
        """Возвращает 'W', 'D', 'L' для указанной команды или None, если матч не сыгран."""
        if not self.played:
            return None
        if team == self.team1:
            gf, ga = self.score1, self.score2
        elif team == self.team2:
            gf, ga = self.score2, self.score1
        else:
            raise ValueError(f"Команда {team} не участвует в этом матче")

        if gf > ga:
            return 'W'
        elif gf < ga:
            return 'L'
        else:
            return 'D'


@dataclass
class TeamStats:
    """Статистика команды в группе."""
    team: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    def to_tuple(self):
        """Для отображения в таблице."""
        return (
            self.team, self.played, self.wins, self.draws, self.losses,
            self.goals_for, self.goals_against, self.goal_diff, self.points
        )


class Group:
    """Группа из 4 команд с матчами round robin."""

    def __init__(self, name: str, teams: List[str]):
        if len(teams) != 4:
            raise ValueError(f"Группа {name} должна содержать ровно 4 команды, получено {len(teams)}")
        self.name = name
        self.teams = teams
        self.matches: List[Match] = [
            Match(t1, t2) for t1, t2 in combinations(teams, 2)
        ]

    def set_result(self, team1: str, team2: str, score1: int, score2: int):
        """Устанавливает результат матча между team1 и team2 (порядок не важен)."""
        for m in self.matches:
            if {m.team1, m.team2} == {team1, team2}:
                if m.team1 == team1:
                    m.score1, m.score2 = score1, score2
                else:
                    m.score1, m.score2 = score2, score1
                return
        raise ValueError(f"Матч {team1} vs {team2} не найден в группе {self.name}")

    def get_match(self, team1: str, team2: str) -> Match:
        for m in self.matches:
            if {m.team1, m.team2} == {team1, team2}:
                return m
        raise ValueError(f"Матч {team1} vs {team2} не найден в группе {self.name}")

    def is_complete(self) -> bool:
        return all(m.played for m in self.matches)

    def compute_stats(self) -> Dict[str, TeamStats]:
        """Считает базовую статистику (без сортировки) по сыгранным матчам."""
        stats = {t: TeamStats(team=t) for t in self.teams}
        for m in self.matches:
            if not m.played:
                continue
            for team, gf, ga in (
                (m.team1, m.score1, m.score2),
                (m.team2, m.score2, m.score1),
            ):
                s = stats[team]
                s.played += 1
                s.goals_for += gf
                s.goals_against += ga
                if gf > ga:
                    s.wins += 1
                    s.points += 3
                elif gf == ga:
                    s.draws += 1
                    s.points += 1
                else:
                    s.losses += 1
        return stats

    def head_to_head(self, team_a: str, team_b: str) -> Tuple[int, int]:
        """Возвращает (очки_a, очки_b) по результату личной встречи (0 если не сыгран)."""
        m = self.get_match(team_a, team_b)
        if not m.played:
            return (0, 0)
        res_a = m.result_for(team_a)
        res_b = m.result_for(team_b)
        pts_map = {'W': 3, 'D': 1, 'L': 0}
        return (pts_map[res_a], pts_map[res_b])

    def standings(self) -> List[TeamStats]:
        """
        Возвращает отсортированную таблицу по правилам FIFA:
        1. Очки
        2. Разница голов
        3. Забитые голы
        4. Личная встреча (при равенстве всех вышестоящих показателей у 2 команд)
        5. Жребий (здесь — оставляем как есть / по алфавиту, помечаем как требующий жребия)

        Fair play очки в данной реализации не учитываются (нет данных о карточках).
        """
        stats = self.compute_stats()

        # Базовая сортировка по (очки, разница, забитые), затем доп. правило head-to-head
        def base_key(s: TeamStats):
            return (-s.points, -s.goal_diff, -s.goals_for)

        ordered = sorted(stats.values(), key=base_key)

        # Проверяем группы команд с одинаковыми (очки, разница, забитые) —
        # если ровно 2 команды равны, сортируем по личной встрече
        i = 0
        result = []
        while i < len(ordered):
            j = i
            while j + 1 < len(ordered) and base_key(ordered[j + 1]) == base_key(ordered[i]):
                j += 1
            tie_group = ordered[i:j + 1]
            if len(tie_group) == 2:
                a, b = tie_group
                pts_a, pts_b = self.head_to_head(a.team, b.team)
                if pts_a != pts_b:
                    tie_group = sorted(tie_group, key=lambda s: s.team != a.team if pts_a > pts_b else s.team == a.team)
                    # пересобираем явно для ясности
                    tie_group = [a, b] if pts_a > pts_b else [b, a]
            # для групп из 3+ команд с равными показателями оставляем порядок как есть
            # (требуется доп. критерий — fair play / жребий, не реализовано)
            result.extend(tie_group)
            i = j + 1

        return result


class Tournament:
    """Контейнер для всех 12 групп турнира."""

    def __init__(self, groups_data: Dict[str, List[str]]):
        if len(groups_data) != 12:
            raise ValueError(f"Должно быть 12 групп, получено {len(groups_data)}")
        self.groups: Dict[str, Group] = {
            name: Group(name, teams) for name, teams in groups_data.items()
        }

    def all_complete(self) -> bool:
        return all(g.is_complete() for g in self.groups.values())

    def get_group_standings(self) -> Dict[str, List[TeamStats]]:
        return {name: g.standings() for name, g in self.groups.items()}

    def best_third_placed(self) -> List[Tuple[str, TeamStats]]:
        """
        Возвращает 8 лучших команд, занявших 3-е место в своих группах,
        отсортированных по (очки, разница, забитые).
        Каждый элемент — (название_группы, TeamStats).
        """
        thirds: List[Tuple[str, TeamStats]] = []
        for name, g in self.groups.items():
            standings = g.standings()
            if len(standings) >= 3:
                thirds.append((name, standings[2]))

        thirds.sort(key=lambda item: (-item[1].points, -item[1].goal_diff, -item[1].goals_for))
        return thirds[:8]

    def qualified_teams(self) -> Dict[str, str]:
        """
        Возвращает словарь {слот: команда} для всех 32 квалифицировавшихся команд.
        Слоты для 1-х и 2-х мест: '1A'..'1L', '2A'..'2L'.
        Слоты для лучших 3-х мест: '3-1'..'3-8' (по рейтингу среди третьих мест),
        с указанием исходной группы для построения сетки.
        """
        result = {}
        standings = self.get_group_standings()
        for group_name, table in standings.items():
            if len(table) >= 1:
                result[f'1{group_name}'] = table[0].team
            if len(table) >= 2:
                result[f'2{group_name}'] = table[1].team

        for rank, (group_name, stats) in enumerate(self.best_third_placed(), start=1):
            result[f'3-{rank}'] = stats.team
            result[f'3-{rank}-group'] = group_name  # вспомогательная информация для bracket_logic

        return result


if __name__ == '__main__':
    # Простой тест на демо-данных
    demo_groups = {
        chr(ord('A') + i): [f'{chr(ord("A") + i)}{j}' for j in range(1, 5)]
        for i in range(12)
    }
    t = Tournament(demo_groups)

    # Заполним группу A результатами вручную для проверки
    g = t.groups['A']
    g.set_result('A1', 'A2', 2, 0)
    g.set_result('A3', 'A4', 1, 1)
    g.set_result('A1', 'A3', 0, 0)
    g.set_result('A2', 'A4', 3, 1)
    g.set_result('A1', 'A4', 1, 0)
    g.set_result('A2', 'A3', 2, 2)

    print("Таблица группы A:")
    for s in g.standings():
        print(s.to_tuple())
