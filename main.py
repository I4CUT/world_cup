"""
ЧМ-2026: Конструктор турнирной сетки.

Главное окно приложения с двумя вкладками:
- "Группы" — базовое распределение команд по местам 1-4 (drag-and-drop)
- "Сетка плейофф" — интерактивная сетка 1/16 финала -> Финал

Связь между вкладками: GroupsTab при каждом изменении вызывает on_change,
BracketTab получает Tournament через tournament_provider, который строит
его из текущей расстановки GroupsTab.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from data import GROUPS
from groups_gui import GroupsTab
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

    # ------------------------------------------------------------------
    def _on_groups_change(self):
        """Вызывается при любом изменении расстановки на вкладке групп."""
        # Пока ничего не делаем автоматически — пользователь сам нажмёт
        # "Сформировать сетку" на вкладке плейофф, когда будет готов.
        pass

    def _get_tournament(self):
        """Строит Tournament на основе текущей расстановки GroupsTab."""
        tournament = self.groups_tab.build_tournament()
        if tournament is None:
            # Возвращаем пустой Tournament — BracketTab сам проверит
            # all_complete() и покажет предупреждение.
            from group_stage import Tournament
            return Tournament(GROUPS)
        return tournament


if __name__ == '__main__':
    app = App()
    app.mainloop()
