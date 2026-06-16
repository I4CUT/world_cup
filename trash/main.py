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
        self.groups_tab = GroupsTab(notebook, GROUPS, on_change=self._on_groups_change,
                                    on_mode_change=self._on_mode_change)
        notebook.add(self.groups_tab, text='Группы')

        # Вкладка сетки плейофф
        self.bracket_tab = BracketTab(notebook, tournament_provider=self._get_tournament)
        notebook.add(self.bracket_tab, text='Сетка плейофф')

        self.notebook = notebook
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
        self._bind_mousewheel_for_tab(0)

    def _on_groups_change(self):
        pass

    def _on_mode_change(self):
        idx = self.notebook.index(self.notebook.select())
        if idx == 0:
            self._unbind_all_mousewheel()
            self._bind_mousewheel_for_tab(0)

    def _on_tab_changed(self, event):
        idx = self.notebook.index(self.notebook.select())
        self._unbind_all_mousewheel()
        self._bind_mousewheel_for_tab(idx)

    def _unbind_all_mousewheel(self):
        for canvas in (self.groups_tab.ext_canvas,
                       self.groups_tab._basic_tab_widget.canvas,
                       self.bracket_tab.canvas):
            canvas.unbind_all('<MouseWheel>')
            canvas.unbind_all('<Shift-MouseWheel>')
            canvas.unbind_all('<Button-4>')
            canvas.unbind_all('<Button-5>')
            canvas.unbind_all('<Shift-Button-4>')
            canvas.unbind_all('<Shift-Button-5>')

    def _bind_mousewheel_for_tab(self, idx):
        if idx == 0:
            if self.groups_tab.mode.get() == 'extended':
                canvas = self.groups_tab.ext_canvas
            else:
                canvas = self.groups_tab._basic_tab_widget.canvas
        else:
            canvas = self.bracket_tab.canvas

        canvas.bind_all('<MouseWheel>',
                        lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units') or 'break')
        canvas.bind_all('<Shift-MouseWheel>',
                        lambda e: canvas.xview_scroll(int(-1 * (e.delta / 120)), 'units') or 'break')
        canvas.bind_all('<Button-4>',
                        lambda e: canvas.yview_scroll(-1, 'units') or 'break')
        canvas.bind_all('<Button-5>',
                        lambda e: canvas.yview_scroll(1, 'units') or 'break')
        canvas.bind_all('<Shift-Button-4>',
                        lambda e: canvas.xview_scroll(-1, 'units') or 'break')
        canvas.bind_all('<Shift-Button-5>',
                        lambda e: canvas.xview_scroll(1, 'units') or 'break')

    def _get_tournament(self):
        tournament = self.groups_tab.build_tournament()
        if tournament is None:
            from group_stage import Tournament
            return Tournament(GROUPS)
        return tournament


if __name__ == '__main__':
    app = App()
    app.mainloop()
