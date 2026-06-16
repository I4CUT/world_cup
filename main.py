"""
ЧМ-2026: Конструктор турнирной сетки.

Главное окно приложения с тремя вкладками:
- "Группы (базовый)"      — расстановка команд по местам (drag-and-drop / клик)
- "Группы (расширенный)"  — ввод счётов всех матчей round robin, с live-таблицей
- "Сетка плейофф"         — интерактивная сетка 1/16 финала -> Финал

Для каждой группы используется ОДИН из двух режимов: приоритет — расширенный
режим, если для соответствующей группы введены все 6 результатов матчей;
иначе берётся расстановка из базовой вкладки. Это позволяет свободно
переключаться между вкладками без переключателей режима внутри вкладки —
просто заполняешь данные в любой из них.

Каждая вкладка сама привязывает обработчики колеса мыши (bind_all с add='+'
и проверкой "курсор сейчас над этой вкладкой") — поэтому скролл работает
независимо на каждой вкладке без необходимости вручную перепривязывать
обработчики при переключении.
"""

import tkinter as tk
from tkinter import ttk

from data import GROUPS
from group_stage import Tournament
from groups_gui import GroupsTab as BasicGroupsTab
from groups_gui_extended import ExtendedGroupsTab
from bracket_gui import BracketTab


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('ЧМ-2026 — Конструктор турнирной сетки')
        self.geometry('1400x850')

        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True)

        # Вкладка "Группы (базовый)"
        self.basic_tab = BasicGroupsTab(notebook, GROUPS, on_change=self._on_groups_change)
        notebook.add(self.basic_tab, text='Группы (базовый)')

        # Вкладка "Группы (расширенный)"
        self.extended_tab = ExtendedGroupsTab(notebook, GROUPS, on_change=self._on_groups_change)
        notebook.add(self.extended_tab, text='Группы (расширенный)')

        # Вкладка сетки плейофф
        self.bracket_tab = BracketTab(notebook, tournament_provider=self._get_tournament)
        notebook.add(self.bracket_tab, text='Сетка плейофф')

        self.notebook = notebook

    def _on_groups_change(self):
        pass

    def _get_tournament(self) -> Tournament:
        """
        Строит итоговый Tournament, объединяя данные из обеих вкладок групп.

        Для каждой группы: если на расширенной вкладке введены все 6
        результатов матчей — используется она; иначе — расстановка по
        местам с базовой вкладки (если заполнена); если ни одна вкладка
        не даёт данных по группе — группа остаётся незаполненной, и
        дальнейшие проверки (all_complete) в BracketTab сообщат об этом.
        """
        tournament = Tournament(GROUPS)

        for group_name in GROUPS:
            ext_group = self.extended_tab.get_group_result(group_name) \
                if hasattr(self.extended_tab, 'get_group_result') else None

            if ext_group is not None:
                g_dst = tournament.groups[group_name]
                for m in ext_group.matches:
                    if m.played:
                        g_dst.set_result(m.team1, m.team2, m.score1, m.score2)
                continue

            # Фоллбэк на расширенную вкладку через прямой доступ к блокам
            # (на случай если get_group_result недоступен в текущей версии модуля)
            ext_block = self.extended_tab._ext_blocks.get(group_name)
            if ext_block is not None and ext_block.is_complete():
                g_src = ext_block.get_group_for_tournament()
                if g_src is not None:
                    g_dst = tournament.groups[group_name]
                    for m in g_src.matches:
                        if m.played:
                            g_dst.set_result(m.team1, m.team2, m.score1, m.score2)
                    continue

            basic_block = self.basic_tab.blocks.get(group_name)
            if basic_block is not None:
                standings = basic_block.get_standings()
                if standings is not None:
                    t1, t2, t3, t4 = standings
                    g_dst = tournament.groups[group_name]
                    g_dst.set_result(t1, t2, 1, 0)
                    g_dst.set_result(t1, t3, 2, 0)
                    g_dst.set_result(t1, t4, 3, 0)
                    g_dst.set_result(t2, t3, 1, 0)
                    g_dst.set_result(t2, t4, 2, 0)
                    g_dst.set_result(t3, t4, 1, 0)

        return tournament


if __name__ == '__main__':
    app = App()
    app.mainloop()
