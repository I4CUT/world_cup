"""
Модуль формирования итогового HTML-отчёта ЧМ-2026.

Отчёт включает:
- итоговую расстановку всех 12 групп (таблицы 1-4 место)
- результаты всех матчей сетки плейофф (1/16 -> Финал, матч за 3-е место)
- итогового чемпиона, финалиста и бронзового призёра

Используется и из вкладки "Группы" (если сетка ещё не сформирована —
выводится только часть по группам), и из вкладки "Сетка плейофф".
"""

import html
from datetime import datetime

from group_stage import Tournament
from bracket_logic import Bracket, ROUND_OF_32_FIXTURES


ROUND_TITLES_RU = {
    'R32': '1/16 финала',
    'R16': '1/8 финала',
    'QF': '1/4 финала',
    'SF': '1/2 финала',
    'F': 'Финал',
    '3RD': 'Матч за 3-е место',
}

ROUND_ORDER = ['R32', 'R16', 'QF', 'SF', 'F', '3RD']

ROUND_MATCH_ORDER = {
    'R32': [mid for mid, _, _ in ROUND_OF_32_FIXTURES],
    'R16': ['R16-1', 'R16-2', 'R16-3', 'R16-4', 'R16-5', 'R16-6', 'R16-7', 'R16-8'],
    'QF': ['QF-1', 'QF-2', 'QF-3', 'QF-4'],
    'SF': ['SF-1', 'SF-2'],
    'F': ['FINAL'],
    '3RD': ['3RD'],
}


def _esc(text: str) -> str:
    return html.escape(str(text))


def _build_groups_section(tournament: Tournament) -> str:
    """Формирует HTML-блок с таблицами итоговых мест по всем группам."""
    parts = ['<h2>Группы — итоговая расстановка</h2>']
    parts.append('<div class="groups-grid">')

    standings = tournament.get_group_standings()
    for group_name in sorted(standings.keys()):
        table = standings[group_name]
        parts.append('<div class="group-card">')
        parts.append(f'<h3>Группа {_esc(group_name)}</h3>')
        parts.append('<table>')
        parts.append('<tr><th>#</th><th>Команда</th><th>И</th><th>В</th><th>Н</th>'
                      '<th>П</th><th>ЗГ</th><th>ПГ</th><th>+/-</th><th>О</th></tr>')
        for i, s in enumerate(table, start=1):
            row_class = 'qualified' if i <= 2 else ('third-place' if i == 3 else '')
            parts.append(
                f'<tr class="{row_class}"><td>{i}</td><td>{_esc(s.team)}</td>'
                f'<td>{s.played}</td><td>{s.wins}</td><td>{s.draws}</td><td>{s.losses}</td>'
                f'<td>{s.goals_for}</td><td>{s.goals_against}</td>'
                f'<td>{"+" if s.goal_diff > 0 else ""}{s.goal_diff}</td><td>{s.points}</td></tr>'
            )
        parts.append('</table>')
        parts.append('</div>')

    parts.append('</div>')

    # Лучшие 3-и места
    thirds = tournament.best_third_placed()
    if thirds:
        parts.append('<h3>Лучшие команды с 3-х мест (проходят в плейофф)</h3>')
        parts.append('<table class="thirds-table">')
        parts.append('<tr><th>#</th><th>Группа</th><th>Команда</th><th>О</th><th>+/-</th><th>ЗГ</th></tr>')
        for i, (grp, s) in enumerate(thirds, start=1):
            parts.append(
                f'<tr><td>{i}</td><td>{_esc(grp)}</td><td>{_esc(s.team)}</td>'
                f'<td>{s.points}</td><td>{"+" if s.goal_diff > 0 else ""}{s.goal_diff}</td>'
                f'<td>{s.goals_for}</td></tr>'
            )
        parts.append('</table>')

    return '\n'.join(parts)


def _team_or_dash(team) -> str:
    return _esc(team) if team else '—'


def _build_bracket_section(bracket: Bracket) -> str:
    """Формирует HTML-блок с результатами сетки плейофф по раундам."""
    parts = ['<h2>Сетка плейофф</h2>']

    for round_name in ROUND_ORDER:
        order = ROUND_MATCH_ORDER[round_name]
        parts.append(f'<h3>{ROUND_TITLES_RU[round_name]}</h3>')
        parts.append('<table class="bracket-table">')
        parts.append('<tr><th>Матч</th><th>Команда 1</th><th>Команда 2</th><th>Победитель</th></tr>')
        for match_id in order:
            m = bracket.get_match(match_id)
            t1_class = 'winner' if m.winner and m.winner == m.team1 else ''
            t2_class = 'winner' if m.winner and m.winner == m.team2 else ''
            parts.append(
                f'<tr><td>{_esc(match_id)}</td>'
                f'<td class="{t1_class}">{_team_or_dash(m.team1)}</td>'
                f'<td class="{t2_class}">{_team_or_dash(m.team2)}</td>'
                f'<td><strong>{_team_or_dash(m.winner)}</strong></td></tr>'
            )
        parts.append('</table>')

    champ = bracket.champion()
    third = bracket.get_match('3RD').winner
    final = bracket.get_match('FINAL')
    runner_up = None
    if final.winner and final.team1 and final.team2:
        runner_up = final.team2 if final.winner == final.team1 else final.team1

    parts.append('<div class="podium">')
    parts.append('<h3>Итоги турнира</h3>')
    parts.append('<ul>')
    parts.append(f'<li>🥇 Чемпион: <strong>{_team_or_dash(champ)}</strong></li>')
    parts.append(f'<li>🥈 Финалист: <strong>{_team_or_dash(runner_up)}</strong></li>')
    parts.append(f'<li>🥉 3-е место: <strong>{_team_or_dash(third)}</strong></li>')
    parts.append('</ul>')
    parts.append('</div>')

    return '\n'.join(parts)


_CSS = """
body { font-family: Arial, Helvetica, sans-serif; margin: 20px; color: #222; }
h1 { border-bottom: 3px solid #333; padding-bottom: 8px; }
h2 { margin-top: 36px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
h3 { margin-top: 20px; }
table { border-collapse: collapse; margin-bottom: 12px; font-size: 13px; }
table th, table td { border: 1px solid #999; padding: 4px 8px; text-align: center; }
table th { background: #eee; }
table td:nth-child(2) { text-align: left; }
.groups-grid { display: flex; flex-wrap: wrap; gap: 16px; }
.group-card { flex: 0 0 auto; }
.group-card table td:nth-child(2) { text-align: left; }
tr.qualified td { background: #e6f4ea; }
tr.third-place td { background: #fff7e0; }
.bracket-table td.winner { background: #cdeacb; font-weight: bold; }
.bracket-table { width: 100%; max-width: 600px; }
.bracket-table td:nth-child(2), .bracket-table td:nth-child(3), .bracket-table td:nth-child(4) {
    text-align: left;
}
.podium ul { font-size: 18px; line-height: 1.8; list-style: none; padding-left: 0; }
.timestamp { color: #777; font-size: 12px; margin-top: 4px; }
"""


def generate_report_html(tournament: Tournament, bracket: Bracket | None = None) -> str:
    """
    Генерирует полный HTML-отчёт по турниру.

    tournament: объект Tournament с заполненными результатами групп.
    bracket: объект Bracket (если сетка плейофф уже сформирована),
             либо None — тогда раздел сетки не включается.
    """
    parts = []
    parts.append('<!DOCTYPE html>')
    parts.append('<html lang="ru">')
    parts.append('<head>')
    parts.append('<meta charset="utf-8">')
    parts.append('<title>ЧМ-2026 — Отчёт по турнирной сетке</title>')
    parts.append(f'<style>{_CSS}</style>')
    parts.append('</head>')
    parts.append('<body>')

    parts.append('<h1>ЧМ-2026 — Отчёт по турнирной сетке</h1>')
    timestamp = datetime.now().strftime('%d.%m.%Y %H:%M')
    parts.append(f'<div class="timestamp">Сформировано: {_esc(timestamp)}</div>')

    parts.append(_build_groups_section(tournament))

    if bracket is not None:
        parts.append(_build_bracket_section(bracket))
    else:
        parts.append('<h2>Сетка плейофф</h2>')
        parts.append('<p><em>Сетка плейофф ещё не сформирована.</em></p>')

    parts.append('</body>')
    parts.append('</html>')

    return '\n'.join(parts)


def save_report(path: str, tournament: Tournament, bracket: Bracket | None = None) -> None:
    """Генерирует и сохраняет HTML-отчёт по указанному пути."""
    content = generate_report_html(tournament, bracket)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


if __name__ == '__main__':
    from data import GROUPS

    tournament = Tournament(GROUPS)
    for group_name, teams in GROUPS.items():
        t1, t2, t3, t4 = teams[1], teams[0], teams[3], teams[2]
        g = tournament.groups[group_name]
        g.set_result(t1, t2, 1, 0)
        g.set_result(t1, t3, 2, 0)
        g.set_result(t1, t4, 3, 0)
        g.set_result(t2, t3, 1, 0)
        g.set_result(t2, t4, 2, 0)
        g.set_result(t3, t4, 1, 0)

    bracket = Bracket(tournament)
    for round_name in ['R32', 'R16', 'QF', 'SF']:
        for m in bracket.get_round(round_name):
            if bracket.is_ready(m.match_id):
                bracket.set_winner(m.match_id, m.team1)
    final = bracket.get_match('FINAL')
    bracket.set_winner('FINAL', final.team1)
    third = bracket.get_match('3RD')
    bracket.set_winner('3RD', third.team1)

    save_report('/tmp/test_report.html', tournament, bracket)
    print('Отчёт сохранён в /tmp/test_report.html')
