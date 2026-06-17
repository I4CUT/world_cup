"""
Загрузка реальных результатов группового этапа ЧМ-2026 из открытого
источника openfootball/worldcup.json (общественное достояние, без
API-ключа): https://github.com/openfootball/worldcup.json

Формат одного матча в их JSON:
    {"round": "Matchday 7", "date": "2026-06-17", "team1": "England",
     "team2": "Croatia", "group": "Group L",
     "score": {"ft": [1, 0], "ht": [0, 0]}}

Поле "score" присутствует только у уже сыгранных матчей. Названия команд
у источника не всегда совпадают с названиями в data.py (например
"Ivory Coast" вместо "Côte d'Ivoire", "USA" вместо "United States") —
NAME_ALIASES ниже приводит их к именам из data.py.

ВАЖНО: автор источника обновляет данные вручную, иногда с задержкой
(см. README репозитория) — поэтому это не гарантированно мгновенный live-
фид, а лучшее доступное открытое решение без API-ключей и без оплаты.
Если матч ещё не отражён в источнике, get_real_results() просто не
вернёт по нему запись, и существующее значение в приложении не меняется.
"""

import json
import urllib.request
import urllib.error
from typing import Optional

WORLDCUP_JSON_URL = 'https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json'

# Приведение названий команд из источника к названиям, используемым в data.py
NAME_ALIASES: dict[str, str] = {
    'USA': 'United States',
    'Ivory Coast': "Côte d'Ivoire",
    'Cote dIvoire': "Côte d'Ivoire",
    "Côte d'Ivoire": "Côte d'Ivoire",
    'Cape Verde': 'Cabo Verde',
    'Iran': 'IR Iran',
    'Czech Republic': 'Czechia',
    'DR Congo': 'Congo DR',
    'Korea Republic': 'South Korea',
    'South Korea': 'South Korea',
    'Turkey': 'Türkiye',
    'Türkiye': 'Türkiye',
}


def _normalize_team_name(name: str) -> str:
    return NAME_ALIASES.get(name, name)


class LiveDataError(Exception):
    """Ошибка при получении или разборе данных о результатах матчей."""
    pass


def fetch_raw_schedule(timeout: float = 10.0) -> dict:
    """
    Скачивает JSON с расписанием/результатами ЧМ-2026.
    Бросает LiveDataError при сетевых проблемах или некорректном формате.
    """
    try:
        req = urllib.request.Request(
            WORLDCUP_JSON_URL,
            headers={'User-Agent': 'wc2026-bracket-app/1.0'}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        raise LiveDataError(f'Не удалось подключиться к источнику данных: {e}') from e
    except TimeoutError as e:
        raise LiveDataError('Превышено время ожидания ответа от источника данных.') from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LiveDataError(f'Источник вернул некорректный JSON: {e}') from e

    if 'matches' not in data:
        raise LiveDataError('В ответе источника отсутствует поле "matches".')

    return data


def get_real_results(group_teams: dict[str, list[str]],
                      timeout: float = 10.0) -> dict[str, dict[tuple, tuple]]:
    """
    Возвращает реальные результаты сыгранных матчей группового этапа.

    group_teams: {group_name: [team1, team2, team3, team4]} — состав групп
                 как в data.py (нужен, чтобы вычислить индексы команд
                 внутри группы для score_vars в GroupBlockExtended).

    Возвращает: {group_name: {(i, j): (score1, score2), ...}}
    где i, j — индексы команд в group_teams[group_name] (i < j), а
    (score1, score2) — счёт в порядке (team[i], team[j]), то есть уже
    приведённый к тому порядку, в котором группа хранит свои матчи
    (см. group_stage.Group, itertools.combinations).

    Матчи, для которых источник не даёт результата (поле "score"
    отсутствует, либо команда — ещё не определившийся плейсхолдер вида
    "UEFA Path D winner"), просто не включаются в результат.
    """
    data = fetch_raw_schedule(timeout=timeout)

    # group_name (как в data.py, например 'A') -> {team_name: index}
    team_index: dict[str, dict[str, int]] = {
        group_name: {team: idx for idx, team in enumerate(teams)}
        for group_name, teams in group_teams.items()
    }

    results: dict[str, dict[tuple, tuple]] = {g: {} for g in group_teams}

    for match in data['matches']:
        group_field = match.get('group')
        if not group_field or not group_field.startswith('Group '):
            continue  # это матч плейофф (Round of 32 и далее) — не интересует нас здесь

        group_name = group_field.replace('Group ', '').strip()
        if group_name not in team_index:
            continue

        score = match.get('score')
        if not score or 'ft' not in score:
            continue  # матч ещё не сыгран

        ft = score['ft']
        if not isinstance(ft, list) or len(ft) != 2:
            continue

        raw_team1 = match.get('team1', '')
        raw_team2 = match.get('team2', '')
        team1 = _normalize_team_name(raw_team1)
        team2 = _normalize_team_name(raw_team2)

        idx_map = team_index[group_name]
        if team1 not in idx_map or team2 not in idx_map:
            # Одна из команд — ещё не определившийся плейсхолдер
            # (например "UEFA Path D winner") или неизвестное название.
            continue

        i1, i2 = idx_map[team1], idx_map[team2]
        s1, s2 = ft[0], ft[1]

        if i1 < i2:
            results[group_name][(i1, i2)] = (s1, s2)
        else:
            results[group_name][(i2, i1)] = (s2, s1)

    return results


if __name__ == '__main__':
    from data import GROUPS

    try:
        results = get_real_results(GROUPS)
    except LiveDataError as e:
        print(f'Ошибка: {e}')
    else:
        total = sum(len(v) for v in results.values())
        print(f'Найдено результатов: {total}')
        for group_name, matches in results.items():
            if matches:
                print(f'  Группа {group_name}: {matches}')
