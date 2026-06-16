"""
GUI вкладки сетки плейофф ЧМ-2026.

Вкладка отображает сетку в виде колонок раундов (1/16, 1/8, 1/4, 1/2, Финал,
матч за 3-е место). Каждый матч — это карточка с двумя кнопками-командами;
клик по названию команды выбирает её победителем, после чего она
автоматически "продвигается" в следующий матч.

Каждый следующий раунд визуально ЦЕНТРИРУЕТСЯ относительно двух матчей
предыдущего раунда, из которых он формируется (классический вид турнирной
сетки) — реализовано через place() с вычисленными координатами в
_compute_layout().

Фон вкладки оформлен как футбольное поле сверху, в горизонтальной
ориентации (ворота слева и справа) — путь от 1/16 финала к Финалу читается
как путь от одних ворот к другим, см. pitch_theme.

Вкладка получает на вход уже сформированный объект Tournament (с заполненными
результатами группового этапа) и строит на его основе объект Bracket.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from bracket_logic import Bracket, BracketMatch
from group_stage import Tournament
from report import save_report
import pitch_theme

PALETTE = {
    'bg_main':    '#1a1f2e',
    'bg_card':    '#242938',
    'bg_header':  '#2d3349',
    'bg_match':   '#1e2336',
    'fg_main':    '#e8eaf0',
    'fg_dim':     '#8892aa',
    'fg_accent':  '#4fc3f7',
    'fg_green':   '#69f0ae',
    'fg_yellow':  '#ffd740',
    'border':     '#363d56',
    'btn_bg':     '#2979ff',
    'btn_hover':  '#448aff',
    'winner_bg':  '#1a3a2a',
}

ROUND_TITLES = {
    'R32': '1/16 финала',
    'R16': '1/8 финала',
    'QF': '1/4 финала',
    'SF': '1/2 финала',
    'F': 'Финал',
    '3RD': 'Матч за 3-е место',
}

ROUND_ORDER = ['R32', 'R16', 'QF', 'SF', 'F']

ROUND_MATCH_ORDER = {
    'R32': ['M73', 'M75', 'M74', 'M77', 'M76', 'M78', 'M79', 'M80',
            'M83', 'M84', 'M81', 'M82', 'M86', 'M88', 'M85', 'M87'],
    'R16': ['R16-1', 'R16-2', 'R16-3', 'R16-4', 'R16-5', 'R16-6', 'R16-7', 'R16-8'],
    'QF': ['QF-1', 'QF-2', 'QF-3', 'QF-4'],
    'SF': ['SF-1', 'SF-2'],
    'F': ['FINAL'],
}

MATCH_SOURCES = {
    'R16-1': ('M73', 'M75'),
    'R16-2': ('M74', 'M77'),
    'R16-3': ('M76', 'M78'),
    'R16-4': ('M79', 'M80'),
    'R16-5': ('M83', 'M84'),
    'R16-6': ('M81', 'M82'),
    'R16-7': ('M86', 'M88'),
    'R16-8': ('M85', 'M87'),
    'QF-1': ('R16-1', 'R16-2'),
    'QF-2': ('R16-3', 'R16-4'),
    'QF-3': ('R16-5', 'R16-6'),
    'QF-4': ('R16-7', 'R16-8'),
    'SF-1': ('QF-1', 'QF-2'),
    'SF-2': ('QF-3', 'QF-4'),
    'FINAL': ('SF-1', 'SF-2'),
    '3RD': ('SF-1', 'SF-2'),
}

MATCH_WIDTH = 200
MATCH_HEIGHT = 70
MATCH_GAP_R32 = 14
COLUMN_GAP = 60


class BracketTab(ttk.Frame):
    """Вкладка с интерактивной сеткой плейофф."""

    def __init__(self, master, tournament_provider, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.tournament_provider = tournament_provider
        self.bracket = None
        self.match_widgets = {}
        self._build_ui()

    def _build_ui(self):
        top_bar = tk.Frame(self, bg=PALETTE['bg_header'], pady=8)
        top_bar.pack(side='top', fill='x')

        self.rebuild_btn = tk.Button(
            top_bar, text='Сформировать сетку по итогам групп',
            bg=PALETTE['btn_bg'], fg='white', relief='flat',
            font=('Segoe UI', 10, 'bold'), padx=12, pady=4,
            activebackground=PALETTE['btn_hover'],
            cursor='hand2', command=self.rebuild_bracket
        )
        self.rebuild_btn.pack(side='left', padx=10)

        self.champion_label = tk.Label(top_bar, text='', bg=PALETTE['bg_header'],
                                        fg=PALETTE['fg_green'],
                                        font=('Segoe UI', 11, 'bold'))
        self.champion_label.pack(side='left', padx=20)

        self.save_report_btn = tk.Button(
            top_bar, text='Сохранить отчёт (HTML)',
            bg=PALETTE['bg_card'], fg=PALETTE['fg_main'], relief='flat',
            font=('Segoe UI', 9), padx=10, pady=3,
            activebackground=PALETTE['border'], cursor='hand2',
            command=self.save_report_dialog
        )
        self.save_report_btn.pack(side='right', padx=10)

        main_container = tk.Frame(self, bg=pitch_theme.GRASS_DARK)
        main_container.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(main_container, bg=pitch_theme.GRASS_DARK,
                                 highlightthickness=0, borderwidth=0)
        v_scroll = ttk.Scrollbar(main_container, orient='vertical', command=self.canvas.yview)
        h_scroll = ttk.Scrollbar(main_container, orient='horizontal', command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')

        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)

        self.inner_frame = tk.Frame(self.canvas, bg=pitch_theme.GRASS_DARK)
        self.inner_frame_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')

        self.inner_frame.bind('<Configure>', self._on_inner_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        self._bind_mousewheel(self.canvas)

        self.round_frames = {}
        self.round_col_frames = {}
        for col, round_name in enumerate(ROUND_ORDER):
            col_frame = tk.Frame(self.inner_frame, bg=pitch_theme.GRASS_DARK)
            col_frame.grid(row=0, column=col, sticky='n', padx=COLUMN_GAP // 2, pady=16)

            title = tk.Label(col_frame, text=ROUND_TITLES[round_name],
                              bg=pitch_theme.GRASS_DARK, fg=PALETTE['fg_accent'],
                              font=('Segoe UI', 11, 'bold'))
            title.pack(pady=(0, 10))

            matches_frame = tk.Frame(col_frame, bg=pitch_theme.GRASS_DARK,
                                      width=MATCH_WIDTH, height=300)
            matches_frame.pack()
            matches_frame.pack_propagate(False)
            self.round_frames[round_name] = matches_frame
            self.round_col_frames[round_name] = col_frame

        third_col = tk.Frame(self.inner_frame, bg=pitch_theme.GRASS_DARK)
        third_col.grid(row=1, column=len(ROUND_ORDER) - 2, sticky='n', padx=COLUMN_GAP // 2, pady=(30, 0))
        title = tk.Label(third_col, text=ROUND_TITLES['3RD'],
                          bg=pitch_theme.GRASS_DARK, fg=PALETTE['fg_accent'],
                          font=('Segoe UI', 11, 'bold'))
        title.pack(pady=(0, 10))
        third_matches_frame = tk.Frame(third_col, bg=pitch_theme.GRASS_DARK,
                                        width=MATCH_WIDTH, height=MATCH_HEIGHT)
        third_matches_frame.pack()
        third_matches_frame.pack_propagate(False)
        self.round_frames['3RD'] = third_matches_frame

        self.placeholder_label = tk.Label(
            self.round_frames['R32'],
            text='Сначала заполните результаты группового этапа\nи нажмите "Сформировать сетку".',
            bg=pitch_theme.GRASS_DARK, fg=PALETTE['fg_dim'],
            font=('Segoe UI', 11), justify='center'
        )
        self.placeholder_label.place(relx=0.5, rely=0.3, anchor='center')

    def _bind_mousewheel(self, canvas):
        self._mouse_over_tab = False

        self.bind('<Enter>', lambda e: setattr(self, '_mouse_over_tab', True))
        self.bind('<Leave>', lambda e: setattr(self, '_mouse_over_tab', False))

        def on_mousewheel(event):
            if not self._mouse_over_tab:
                return
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        def on_mousewheel_linux_up(event):
            if not self._mouse_over_tab:
                return
            canvas.yview_scroll(-1, 'units')

        def on_mousewheel_linux_down(event):
            if not self._mouse_over_tab:
                return
            canvas.yview_scroll(1, 'units')

        def on_shift_mousewheel(event):
            if not self._mouse_over_tab:
                return
            canvas.xview_scroll(int(-1 * (event.delta / 120)), 'units')

        def on_shift_mousewheel_linux_up(event):
            if not self._mouse_over_tab:
                return
            canvas.xview_scroll(-1, 'units')

        def on_shift_mousewheel_linux_down(event):
            if not self._mouse_over_tab:
                return
            canvas.xview_scroll(1, 'units')

        canvas.bind_all('<MouseWheel>', on_mousewheel, add='+')
        canvas.bind_all('<Shift-MouseWheel>', on_shift_mousewheel, add='+')
        canvas.bind_all('<Button-4>', on_mousewheel_linux_up, add='+')
        canvas.bind_all('<Button-5>', on_mousewheel_linux_down, add='+')
        canvas.bind_all('<Shift-Button-4>', on_shift_mousewheel_linux_up, add='+')
        canvas.bind_all('<Shift-Button-5>', on_shift_mousewheel_linux_down, add='+')

    def _on_inner_configure(self, event):
        pitch_theme.repaint(self.canvas, orientation='horizontal')

    def _on_canvas_configure(self, event):
        pitch_theme.repaint(self.canvas, orientation='horizontal')

    def rebuild_bracket(self):
        tournament = self.tournament_provider()

        if not tournament.all_complete():
            messagebox.showwarning(
                'Группы не заполнены',
                'Не все матчи группового этапа имеют результат.\n'
                'Заполните все результаты на вкладке групп, прежде чем строить сетку плейофф.'
            )
            return

        self.bracket = Bracket(tournament)
        self._redraw()

    def save_report_dialog(self):
        tournament = self.tournament_provider()

        if not tournament.all_complete():
            messagebox.showwarning(
                'Группы не заполнены',
                'Не все матчи группового этапа имеют результат.\n'
                'Заполните все результаты на вкладке групп, прежде чем сохранять отчёт.'
            )
            return

        if self.bracket is None:
            if not messagebox.askyesno(
                'Сетка не сформирована',
                'Сетка плейофф ещё не сформирована (нажмите "Сформировать сетку").\n'
                'Сохранить отчёт только по группам, без сетки плейофф?'
            ):
                return

        path = filedialog.asksaveasfilename(
            title='Сохранить отчёт',
            defaultextension='.html',
            filetypes=[('HTML файлы', '*.html'), ('Все файлы', '*.*')],
            initialfile='wc2026_report.html',
        )
        if not path:
            return

        try:
            save_report(path, tournament, self.bracket)
        except OSError as e:
            messagebox.showerror('Ошибка сохранения', f'Не удалось сохранить файл:\n{e}')
            return

        messagebox.showinfo('Готово', f'Отчёт сохранён:\n{path}')

    def _compute_layout(self):
        y_center = {}

        step = MATCH_HEIGHT + MATCH_GAP_R32
        for i, match_id in enumerate(ROUND_MATCH_ORDER['R32']):
            y_center[match_id] = MATCH_HEIGHT / 2 + i * step

        for round_name in ('R16', 'QF', 'SF', 'F'):
            for match_id in ROUND_MATCH_ORDER[round_name]:
                src1, src2 = MATCH_SOURCES[match_id]
                y_center[match_id] = (y_center[src1] + y_center[src2]) / 2

        src1, src2 = MATCH_SOURCES['3RD']
        y_center['3RD'] = (y_center[src1] + y_center[src2]) / 2

        return y_center

    def _redraw(self):
        for frame in self.round_frames.values():
            for child in frame.winfo_children():
                child.destroy()
        self.match_widgets.clear()

        if self.bracket is None:
            tk.Label(
                self.round_frames['R32'],
                text='Сначала заполните результаты группового этапа\nи нажмите "Сформировать сетку".',
                bg=pitch_theme.GRASS_DARK, fg=PALETTE['fg_dim'],
                font=('Segoe UI', 11), justify='center'
            ).place(relx=0.5, rely=0.3, anchor='center')
            self.champion_label.configure(text='')
            return

        y_center = self._compute_layout()

        total_height = y_center[ROUND_MATCH_ORDER['R32'][-1]] + MATCH_HEIGHT / 2 + 10

        for round_name in ROUND_ORDER:
            frame = self.round_frames[round_name]
            frame.configure(height=int(total_height))
            for match_id in ROUND_MATCH_ORDER[round_name]:
                m = self.bracket.get_match(match_id)
                self._create_match_widget(frame, m, y_center[match_id])

        third_frame = self.round_frames['3RD']
        third_frame.configure(height=MATCH_HEIGHT)
        m3 = self.bracket.get_match('3RD')
        self._create_match_widget(third_frame, m3, MATCH_HEIGHT / 2)

        self._update_champion_label()

        self.inner_frame.update_idletasks()
        pitch_theme.repaint(self.canvas, orientation='horizontal')

    def _create_match_widget(self, parent, m, y_center):
        frame = tk.Frame(parent, bg=PALETTE['bg_card'],
                         relief='solid', borderwidth=1,
                         highlightbackground=PALETTE['border'])
        frame.place(x=0, y=y_center - MATCH_HEIGHT / 2, width=MATCH_WIDTH, height=MATCH_HEIGHT)
        frame.pack_propagate(False)

        label_text = m.match_id if m.round_name == 'R32' else ''
        if label_text:
            tk.Label(frame, text=label_text, bg=PALETTE['bg_card'],
                     fg=PALETTE['fg_dim'], font=('Segoe UI', 8)).pack(anchor='w', padx=4, pady=(2, 0))

        btn1 = tk.Button(
            frame, text=self._team_text(m, m.team1), width=24, anchor='w',
            bg=PALETTE['bg_match'], fg=PALETTE['fg_main'],
            relief='raised', font=('Segoe UI', 9),
            command=lambda: self._on_pick(m.match_id, m.team1)
        )
        btn1.pack(fill='x', pady=2, padx=4)

        btn2 = tk.Button(
            frame, text=self._team_text(m, m.team2), width=24, anchor='w',
            bg=PALETTE['bg_match'], fg=PALETTE['fg_main'],
            relief='raised', font=('Segoe UI', 9),
            command=lambda: self._on_pick(m.match_id, m.team2)
        )
        btn2.pack(fill='x', pady=2, padx=4)

        self._style_buttons(m, btn1, btn2)

        self.match_widgets[m.match_id] = {'frame': frame, 'btn1': btn1, 'btn2': btn2}

    @staticmethod
    def _team_text(m, team):
        if team is None:
            return '—'
        return team

    def _style_buttons(self, m, btn1, btn2):
        ready = m.team1 is not None and m.team2 is not None

        for btn, team in ((btn1, m.team1), (btn2, m.team2)):
            if team is None:
                btn.configure(state='disabled', bg=PALETTE['bg_match'], fg=PALETTE['fg_dim'])
                continue

            if not ready:
                btn.configure(state='disabled', bg=PALETTE['bg_match'], fg=PALETTE['fg_dim'])
            else:
                btn.configure(state='normal')
                if m.winner == team:
                    btn.configure(bg=PALETTE['winner_bg'], fg=PALETTE['fg_green'])
                elif m.winner is not None:
                    btn.configure(bg=PALETTE['bg_match'], fg=PALETTE['fg_dim'])
                else:
                    btn.configure(bg=PALETTE['bg_match'], fg=PALETTE['fg_main'])

    def _on_pick(self, match_id, team):
        if team is None or self.bracket is None:
            return
        self.bracket.set_winner(match_id, team)
        self._redraw_styles_only()

    def _redraw_styles_only(self):
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
                text += f'   |   🥉 Бронза: {third_match.winner}'
            self.champion_label.configure(text=text)
        else:
            self.champion_label.configure(text='')


if __name__ == '__main__':
    from data import GROUPS

    root = tk.Tk()
    root.title('Тест: сетка плейофф ЧМ-2026')
    root.geometry('1400x800')

    tournament = Tournament(GROUPS)

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
