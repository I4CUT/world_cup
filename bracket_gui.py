"""
GUI вкладки сетки плейофф ЧМ-2026.

Вкладка отображает сетку в виде колонок раундов (1/16, 1/8, 1/4, 1/2, Финал,
матч за 3-е место). Каждый матч — это кнопка/пара кнопок с названиями команд;
клик по названию команды выбирает её победителем, после чего она
автоматически "продвигается" в следующий матч.

Вкладка получает на вход уже сформированный объект Tournament (с заполненными
результатами группового этапа) и строит на его основе объект Bracket.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from bracket_logic import Bracket, BracketMatch
from group_stage import Tournament


ROUND_TITLES = {
    'R32': '1/16 финала',
    'R16': '1/8 финала',
    'QF': '1/4 финала',
    'SF': '1/2 финала',
    'F': 'Финал',
    '3RD': 'Матч за 3-е место',
}

# Порядок колонок слева -> направо
ROUND_ORDER = ['R32', 'R16', 'QF', 'SF', 'F']

# Порядок матчей внутри каждого раунда (сверху вниз), чтобы визуально
# связи между раундами выглядели логично (матч R16-1 примерно между
# исходными M73/M75 и т.д.)
ROUND_MATCH_ORDER = {
    'R32': ['M73', 'M75', 'M74', 'M77', 'M76', 'M78', 'M79', 'M80',
            'M83', 'M84', 'M81', 'M82', 'M86', 'M88', 'M85', 'M87'],
    'R16': ['R16-1', 'R16-2', 'R16-3', 'R16-4', 'R16-5', 'R16-6', 'R16-7', 'R16-8'],
    'QF': ['QF-1', 'QF-2', 'QF-3', 'QF-4'],
    'SF': ['SF-1', 'SF-2'],
    'F': ['FINAL'],
}


class BracketTab(ttk.Frame):
    """Вкладка с интерактивной сеткой плейофф."""

    def __init__(self, master, tournament_provider, *args, **kwargs):
        """
        tournament_provider: функция без аргументов, возвращающая текущий
        объект Tournament (с заполненными результатами групп). Это позволяет
        вкладке сетки получать актуальные данные из вкладки групп при
        каждом пересчёте.
        """
        super().__init__(master, *args, **kwargs)
        self.tournament_provider = tournament_provider
        self.bracket: Bracket | None = None

        # Виджеты матчей: match_id -> dict с кнопками team1/team2 и фреймом
        self.match_widgets: dict[str, dict] = {}

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        # Верхняя панель с кнопкой пересчёта и информацией о чемпионе
        top_bar = ttk.Frame(self)
        top_bar.pack(side='top', fill='x', padx=10, pady=8)

        self.rebuild_btn = ttk.Button(
            top_bar, text='Сформировать сетку по итогам групп',
            command=self.rebuild_bracket
        )
        self.rebuild_btn.pack(side='left')

        self.champion_label = ttk.Label(top_bar, text='', font=('TkDefaultFont', 11, 'bold'))
        self.champion_label.pack(side='left', padx=20)

        # Прокручиваемая область с сеткой
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(side='top', fill='both', expand=True)

        self.canvas = tk.Canvas(canvas_frame, borderwidth=0, highlightthickness=0)
        h_scroll = ttk.Scrollbar(canvas_frame, orient='horizontal', command=self.canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        self.inner_frame = ttk.Frame(self.canvas)
        self.inner_frame_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')

        self.inner_frame.bind('<Configure>', self._on_inner_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # Колонки раундов
        self.round_frames: dict[str, ttk.Frame] = {}
        for col, round_name in enumerate(ROUND_ORDER):
            col_frame = ttk.Frame(self.inner_frame, padding=10)
            col_frame.grid(row=0, column=col, sticky='n', padx=5)

            title = ttk.Label(col_frame, text=ROUND_TITLES[round_name],
                               font=('TkDefaultFont', 11, 'bold'))
            title.pack(pady=(0, 10))

            matches_frame = ttk.Frame(col_frame)
            matches_frame.pack()
            self.round_frames[round_name] = matches_frame

        # Отдельная колонка для матча за 3-е место
        third_col = ttk.Frame(self.inner_frame, padding=10)
        third_col.grid(row=1, column=len(ROUND_ORDER) - 2, sticky='n', padx=5, pady=(30, 0))
        title = ttk.Label(third_col, text=ROUND_TITLES['3RD'], font=('TkDefaultFont', 11, 'bold'))
        title.pack(pady=(0, 10))
        third_matches_frame = ttk.Frame(third_col)
        third_matches_frame.pack()
        self.round_frames['3RD'] = third_matches_frame

        self.placeholder_label = ttk.Label(
            self.round_frames['R32'],
            text='Сначала заполните результаты группового этапа\nи нажмите "Сформировать сетку".',
            justify='center'
        )
        self.placeholder_label.pack(pady=40)

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_configure(self, event):
        # Позволяет внутреннему фрейму занимать минимум всю высоту канваса
        pass

    # ------------------------------------------------------------------
    def rebuild_bracket(self):
        """Пересчитывает Bracket на основе текущего Tournament и перерисовывает UI."""
        tournament: Tournament = self.tournament_provider()

        if not tournament.all_complete():
            messagebox.showwarning(
                'Группы не заполнены',
                'Не все матчи группового этапа имеют результат.\n'
                'Заполните все результаты на вкладке групп, прежде чем строить сетку плейофф.'
            )
            return

        self.bracket = Bracket(tournament)
        self._redraw()

    # ------------------------------------------------------------------
    def _redraw(self):
        # Очищаем все колонки
        for frame in self.round_frames.values():
            for child in frame.winfo_children():
                child.destroy()
        self.match_widgets.clear()

        if self.bracket is None:
            ttk.Label(
                self.round_frames['R32'],
                text='Сначала заполните результаты группового этапа\nи нажмите "Сформировать сетку".',
                justify='center'
            ).pack(pady=40)
            self.champion_label.configure(text='')
            return

        for round_name in ROUND_ORDER:
            frame = self.round_frames[round_name]
            order = ROUND_MATCH_ORDER[round_name]
            for match_id in order:
                m = self.bracket.get_match(match_id)
                self._create_match_widget(frame, m)

        # Матч за 3-е место
        frame3 = self.round_frames['3RD']
        m3 = self.bracket.get_match('3RD')
        self._create_match_widget(frame3, m3)

        self._update_champion_label()

    # ------------------------------------------------------------------
    def _create_match_widget(self, parent, m: BracketMatch):
        """Создаёт виджет одного матча с двумя кнопками-командами."""
        frame = ttk.Frame(parent, relief='groove', borderwidth=1, padding=4)
        frame.pack(pady=8, padx=4, fill='x')

        label_text = m.match_id if m.round_name == 'R32' else ''
        if label_text:
            ttk.Label(frame, text=label_text, font=('TkDefaultFont', 8), foreground='gray').pack(anchor='w')

        btn1 = tk.Button(
            frame, text=self._team_text(m, m.team1), width=22, anchor='w',
            relief='raised',
            command=lambda: self._on_pick(m.match_id, m.team1)
        )
        btn1.pack(fill='x', pady=1)

        btn2 = tk.Button(
            frame, text=self._team_text(m, m.team2), width=22, anchor='w',
            relief='raised',
            command=lambda: self._on_pick(m.match_id, m.team2)
        )
        btn2.pack(fill='x', pady=1)

        self._style_buttons(m, btn1, btn2)

        self.match_widgets[m.match_id] = {'frame': frame, 'btn1': btn1, 'btn2': btn2}

    @staticmethod
    def _team_text(m: BracketMatch, team) -> str:
        if team is None:
            return '—'
        return team

    def _style_buttons(self, m: BracketMatch, btn1: tk.Button, btn2: tk.Button):
        """Включает/выключает кнопки и подсвечивает выбранного победителя."""
        ready = m.team1 is not None and m.team2 is not None

        for btn, team in ((btn1, m.team1), (btn2, m.team2)):
            if team is None:
                btn.configure(state='disabled', bg='SystemButtonFace')
                continue

            if not ready:
                btn.configure(state='disabled', bg='SystemButtonFace')
            else:
                btn.configure(state='normal')
                if m.winner == team:
                    btn.configure(bg='#a6d9a0')  # зелёный — выбран победителем
                elif m.winner is not None:
                    btn.configure(bg='#f0f0f0')  # проигравший — приглушён
                else:
                    btn.configure(bg='SystemButtonFace')

    # ------------------------------------------------------------------
    def _on_pick(self, match_id: str, team):
        if team is None or self.bracket is None:
            return
        self.bracket.set_winner(match_id, team)
        self._redraw_styles_only()

    def _redraw_styles_only(self):
        """Обновляет тексты и стили кнопок без полного перестроения виджетов
        (быстрее и не теряет позицию скролла)."""
        for round_name in ROUND_ORDER + ['3RD']:
            order = ROUND_MATCH_ORDER.get(round_name, ['3RD'] if round_name == '3RD' else [])
            for match_id in order:
                m = self.bracket.get_match(match_id)
                widgets = self.match_widgets.get(match_id)
                if not widgets:
                    continue
                widgets['btn1'].configure(text=self._team_text(m, m.team1))
                widgets['btn2'].configure(text=self._team_text(m, m.team2))
                self._style_buttons(m, widgets['btn1'], widgets['btn2'])

        self._update_champion_label()

    def _update_champion_label(self):
        if self.bracket is None:
            self.champion_label.configure(text='')
            return
        champ = self.bracket.champion()
        third_match = self.bracket.get_match('3RD')
        if champ:
            text = f'🏆 Чемпион: {champ}'
            if third_match.winner:
                text += f'   |   Бронза: {third_match.winner}'
            self.champion_label.configure(text=text)
        else:
            self.champion_label.configure(text='')


if __name__ == '__main__':
    # Автономный тест вкладки на демо-данных с готовым результатом группового этапа
    from data import GROUPS

    root = tk.Tk()
    root.title('Тест: сетка плейофф ЧМ-2026')
    root.geometry('1400x800')

    tournament = Tournament(GROUPS)

    # Заполняем все группы детерминированными результатами для теста
    for name, g in tournament.groups.items():
        results = {
            (0, 1): (2, 0), (0, 2): (1, 0), (0, 3): (3, 0),
            (1, 2): (1, 0), (1, 3): (2, 0), (2, 3): (1, 1),
        }
        for (i, j), (s1, s2) in results.items():
            g.set_result(g.teams[i], g.teams[j], s1, s2)

    tab = BracketTab(root, tournament_provider=lambda: tournament)
    tab.pack(fill='both', expand=True)

    root.mainloop()
