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
from tkinter import messagebox, filedialog
from pathlib import Path
from PIL import Image, ImageTk

from bracket_logic import Bracket, BracketMatch
from group_stage import Tournament
from report import save_report
from groups_gui import PALETTE


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

_HERE = Path(__file__).parent
FLAGS_DIR = _HERE / 'flags_png'

TEAM_ISO: dict[str, str] = {
    'Mexico': 'mx', 'South Africa': 'za', 'South Korea': 'kr', 'Czechia': 'cz',
    'Canada': 'ca', 'Bosnia and Herzegovina': 'ba', 'Qatar': 'qa', 'Switzerland': 'ch',
    'Brazil': 'br', 'Morocco': 'ma', 'Haiti': 'ht', 'Scotland': 'gb-sct',
    'United States': 'us', 'Paraguay': 'py', 'Australia': 'au', 'Türkiye': 'tr',
    'Germany': 'de', 'Curaçao': 'cw', "Côte d'Ivoire": 'ci', 'Ecuador': 'ec',
    'Netherlands': 'nl', 'Japan': 'jp', 'Sweden': 'se', 'Tunisia': 'tn',
    'Belgium': 'be', 'Egypt': 'eg', 'IR Iran': 'ir', 'New Zealand': 'nz',
    'Spain': 'es', 'Cabo Verde': 'cv', 'Saudi Arabia': 'sa', 'Uruguay': 'uy',
    'France': 'fr', 'Senegal': 'sn', 'Iraq': 'iq', 'Norway': 'no',
    'Argentina': 'ar', 'Algeria': 'dz', 'Austria': 'at', 'Jordan': 'jo',
    'Portugal': 'pt', 'Congo DR': 'cd', 'Uzbekistan': 'uz', 'Colombia': 'co',
    'England': 'gb-eng', 'Croatia': 'hr', 'Ghana': 'gh', 'Panama': 'pa',
}

_FLAG_CACHE: dict[str, tk.PhotoImage] = {}


def get_flag(team: str) -> tk.PhotoImage | None:
    iso = TEAM_ISO.get(team)
    if iso is None:
        return None
    if iso in _FLAG_CACHE:
        return _FLAG_CACHE[iso]
    path = FLAGS_DIR / f'{iso}.png'
    if not path.exists():
        return None
    try:
        img = Image.open(path).resize((28, 20), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        _FLAG_CACHE[iso] = photo
        return photo
    except Exception:
        return None


class BracketTab(tk.Frame):
    def __init__(self, master, tournament_provider, *args, **kwargs):
        super().__init__(master, bg=PALETTE['bg_main'], *args, **kwargs)
        self.tournament_provider = tournament_provider
        self.bracket: Bracket | None = None
        self.match_widgets: dict[str, dict] = {}
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

        main_container = tk.Frame(self, bg=PALETTE['bg_main'])
        main_container.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(main_container, bg=PALETTE['bg_main'],
                                 highlightthickness=0, borderwidth=0)
        v_scroll = tk.Scrollbar(main_container, orient='vertical', command=self.canvas.yview)
        h_scroll = tk.Scrollbar(main_container, orient='horizontal', command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')

        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)

        self.inner_frame = tk.Frame(self.canvas, bg=PALETTE['bg_main'])
        self.inner_frame_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')

        self.inner_frame.bind('<Configure>', self._on_inner_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        self._bind_mousewheel(self.canvas)

        self.round_frames: dict[str, tk.Frame] = {}
        for col, round_name in enumerate(ROUND_ORDER):
            col_frame = tk.Frame(self.inner_frame, bg=PALETTE['bg_main'])
            col_frame.grid(row=0, column=col, sticky='n', padx=10)

            title = tk.Label(col_frame, text=ROUND_TITLES[round_name],
                              bg=PALETTE['bg_main'], fg=PALETTE['fg_accent'],
                              font=('Segoe UI', 11, 'bold'))
            title.pack(pady=(0, 10))

            matches_frame = tk.Frame(col_frame, bg=PALETTE['bg_main'])
            matches_frame.pack()
            self.round_frames[round_name] = matches_frame

        third_col = tk.Frame(self.inner_frame, bg=PALETTE['bg_main'])
        third_col.grid(row=1, column=len(ROUND_ORDER) - 2, sticky='n', padx=10, pady=(30, 0))
        title = tk.Label(third_col, text=ROUND_TITLES['3RD'],
                          bg=PALETTE['bg_main'], fg=PALETTE['fg_accent'],
                          font=('Segoe UI', 11, 'bold'))
        title.pack(pady=(0, 10))
        third_matches_frame = tk.Frame(third_col, bg=PALETTE['bg_main'])
        third_matches_frame.pack()
        self.round_frames['3RD'] = third_matches_frame

        self.placeholder_label = tk.Label(
            self.round_frames['R32'],
            text='Сначала заполните результаты группового этапа\nи нажмите "Сформировать сетку".',
            bg=PALETTE['bg_main'], fg=PALETTE['fg_dim'],
            font=('Segoe UI', 11), justify='center'
        )
        self.placeholder_label.pack(pady=40)

    def _bind_mousewheel(self, canvas):
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
            return 'break'

        def on_mousewheel_linux_up(event):
            canvas.yview_scroll(-1, 'units')
            return 'break'

        def on_mousewheel_linux_down(event):
            canvas.yview_scroll(1, 'units')
            return 'break'

        def on_shift_mousewheel(event):
            canvas.xview_scroll(int(-1 * (event.delta / 120)), 'units')
            return 'break'

        canvas.bind_all('<MouseWheel>', on_mousewheel)
        canvas.bind_all('<Shift-MouseWheel>', on_shift_mousewheel)
        canvas.bind_all('<Button-4>', on_mousewheel_linux_up)
        canvas.bind_all('<Button-5>', on_mousewheel_linux_down)

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.inner_frame_id, width=event.width)

    def rebuild_bracket(self):
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

    def save_report_dialog(self):
        tournament: Tournament = self.tournament_provider()

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

    def _redraw(self):
        for frame in self.round_frames.values():
            for child in frame.winfo_children():
                child.destroy()
        self.match_widgets.clear()

        if self.bracket is None:
            tk.Label(
                self.round_frames['R32'],
                text='Сначала заполните результаты группового этапа\nи нажмите "Сформировать сетку".',
                bg=PALETTE['bg_main'], fg=PALETTE['fg_dim'],
                font=('Segoe UI', 11), justify='center'
            ).pack(pady=40)
            self.champion_label.configure(text='')
            return

        for round_name in ROUND_ORDER:
            frame = self.round_frames[round_name]
            order = ROUND_MATCH_ORDER[round_name]
            for match_id in order:
                m = self.bracket.get_match(match_id)
                self._create_match_widget(frame, m)

        frame3 = self.round_frames['3RD']
        m3 = self.bracket.get_match('3RD')
        self._create_match_widget(frame3, m3)

        self._update_champion_label()

        self.inner_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _create_match_widget(self, parent, m: BracketMatch):
        frame = tk.Frame(parent, bg=PALETTE['bg_card'],
                         relief='solid', borderwidth=1,
                         highlightbackground=PALETTE['border'])
        frame.pack(pady=6, padx=4, fill='x')

        label_text = m.match_id if m.round_name == 'R32' else ''
        if label_text:
            tk.Label(frame, text=label_text, bg=PALETTE['bg_card'],
                     fg=PALETTE['fg_dim'], font=('Segoe UI', 8)).pack(anchor='w', padx=4, pady=(2, 0))

        team1 = m.team1
        team2 = m.team2
        flag1 = get_flag(team1) if team1 else None
        flag2 = get_flag(team2) if team2 else None

        btn1 = tk.Button(
            frame, text=self._team_text(m, team1), width=24, anchor='w',
            bg=PALETTE['bg_match'], fg=PALETTE['fg_main'],
            relief='raised', font=('Segoe UI', 9),
            activebackground=PALETTE['border'],
            command=lambda: self._on_pick(m.match_id, team1)
        )
        if flag1:
            btn1.configure(image=flag1, compound='left')
            btn1.image = flag1
        btn1.pack(fill='x', pady=2, padx=4)

        btn2 = tk.Button(
            frame, text=self._team_text(m, team2), width=24, anchor='w',
            bg=PALETTE['bg_match'], fg=PALETTE['fg_main'],
            relief='raised', font=('Segoe UI', 9),
            activebackground=PALETTE['border'],
            command=lambda: self._on_pick(m.match_id, team2)
        )
        if flag2:
            btn2.configure(image=flag2, compound='left')
            btn2.image = flag2
        btn2.pack(fill='x', pady=2, padx=4)

        self._style_buttons(m, btn1, btn2)

        self.match_widgets[m.match_id] = {'frame': frame, 'btn1': btn1, 'btn2': btn2}

    @staticmethod
    def _team_text(m: BracketMatch, team) -> str:
        if team is None:
            return '—'
        return team

    def _style_buttons(self, m: BracketMatch, btn1: tk.Button, btn2: tk.Button):
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

    def _on_pick(self, match_id: str, team):
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

                flag1 = get_flag(m.team1) if m.team1 else None
                flag2 = get_flag(m.team2) if m.team2 else None

                widgets['btn1'].configure(text=self._team_text(m, m.team1))
                if flag1:
                    widgets['btn1'].configure(image=flag1, compound='left')
                    widgets['btn1'].image = flag1
                else:
                    widgets['btn1'].configure(image='', compound='none')

                widgets['btn2'].configure(text=self._team_text(m, m.team2))
                if flag2:
                    widgets['btn2'].configure(image=flag2, compound='left')
                    widgets['btn2'].image = flag2
                else:
                    widgets['btn2'].configure(image='', compound='none')

                self._style_buttons(m, widgets['btn1'], widgets['btn2'])

        self._update_champion_label()

    def _update_champion_label(self):
        if self.bracket is None:
            self.champion_label.configure(text='')
            return
        champ = self.bracket.champion()
        third_match = self.bracket.get_match('3RD')
        if champ:
            champ_flag = get_flag(champ)
            text = f'Чемпион: {champ}'
            if third_match.winner:
                text += f'   |   Бронза: {third_match.winner}'
            self.champion_label.configure(text=text, image=champ_flag, compound='left')
            if champ_flag:
                self.champion_label.image = champ_flag
        else:
            self.champion_label.configure(text='')


if __name__ == '__main__':
    from data import GROUPS

    root = tk.Tk()
    root.title('Тест: сетка плейофф ЧМ-2026')
    root.geometry('1400x800')
    root.configure(bg=PALETTE['bg_main'])

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
