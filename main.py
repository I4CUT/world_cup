"""
ЧМ-2026: Конструктор турнирной сетки.

Главное окно приложения с двумя вкладками:
- "Группы"        — распределение команд (базовый: drag-and-drop;
                    расширенный: ввод счётов всех матчей round robin)
- "Сетка плейофф" — интерактивная сетка 1/16 финала -> Финал
"""

import tkinter as tk
from tkinter import ttk

from data import GROUPS
from groups_gui_extended import GroupsTab   # ← новый модуль с двумя режимами
from bracket_gui import BracketTab


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('ЧМ-2026 — Конструктор турнирной сетки')
        self.geometry('1400x850')

        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True)

        # Вкладка групп
        self.groups_tab = GroupsTab(notebook, GROUPS, on_change=self._on_groups_change)
        notebook.add(self.groups_tab, text='Группы')

        # Вкладка сетки плейофф
        self.bracket_tab = BracketTab(notebook, tournament_provider=self._get_tournament)
        notebook.add(self.bracket_tab, text='Сетка плейофф')

        self.notebook = notebook

    def _on_groups_change(self):
        pass

    def _get_tournament(self):
        tournament = self.groups_tab.build_tournament()
        if tournament is None:
            from group_stage import Tournament
            return Tournament(GROUPS)
        return tournament


if __name__ == '__main__':
    app = App()
    app.mainloop()
