"""
GUI вкладки "Группы (расширенные)" — ввод счётов матчей, с пересчётом
турнирной таблицы в реальном времени. Фон — футбольное поле сверху.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from itertools import combinations
import threading

from group_stage import Tournament, Group
from groups_gui import PALETTE
import pitch_theme
import live_data

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
        from PIL import Image, ImageTk
        img = Image.open(path).resize((28, 20), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        _FLAG_CACHE[iso] = photo
        return photo
    except Exception:
        return None


MATCH_PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]

STANDINGS_HEADERS = ['#', 'Команда', 'И', 'В', 'Н', 'П', 'ЗГ', 'ПГ', '+/−', 'О']


def _make_score_entry(parent, textvariable, on_change_cb) -> tk.Entry:
    def validate(P):
        if P == '':
            return True
        if P.lstrip('0').isdigit() or P == '0':
            return True
        if P.isdigit():
            return True
        return False

    vcmd = parent.register(validate)
    entry = tk.Entry(
        parent,
        textvariable=textvariable,
        validate='key',
        validatecommand=(vcmd, '%P'),
        width=3,
        justify='center',
        font=('Segoe UI', 12, 'bold'),
        bg=PALETTE['entry_bg'],
        fg=PALETTE['entry_fg'],
        insertbackground=PALETTE['entry_fg'],
        relief='flat',
        highlightthickness=2,
        highlightbackground=PALETTE['border'],
        highlightcolor=PALETTE['entry_border'],
    )
    textvariable.trace_add('write', lambda *_: on_change_cb())
    return entry


class GroupBlockExtended(tk.Frame):
    def __init__(self, master, group_name: str, teams: list[str], on_change=None, **kwargs):
        super().__init__(master, bg=PALETTE['bg_card'],
                         highlightthickness=1, highlightbackground=PALETTE['border'],
                         **kwargs)
        self.group_name = group_name
        self.teams = teams
        self.on_change = on_change
        self.score_vars: dict[tuple, tuple] = {}
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=PALETTE['bg_header'])
        hdr.pack(fill='x')
        tk.Label(hdr, text=f'  ГРУППА  {self.group_name}',
                 bg=PALETTE['bg_header'], fg=PALETTE['fg_accent'],
                 font=('Segoe UI', 11, 'bold'), pady=6).pack(side='left')

        body = tk.Frame(self, bg=PALETTE['bg_card'])
        body.pack(fill='both', padx=8, pady=6)

        left = tk.Frame(body, bg=PALETTE['bg_card'])
        left.pack(side='left', anchor='n', padx=(0, 16))

        tk.Label(left, text='Матчи', bg=PALETTE['bg_card'],
                 fg=PALETTE['fg_dim'], font=('Segoe UI', 9)).pack(anchor='w', pady=(0, 4))

        for idx, (i, j) in enumerate(MATCH_PAIRS):
            t1, t2 = self.teams[i], self.teams[j]
            v1, v2 = tk.StringVar(value='0'), tk.StringVar(value='0')
            self.score_vars[(i, j)] = (v1, v2)

            row_bg = PALETTE['bg_match'] if idx % 2 == 0 else PALETTE['bg_match_alt']
            row = tk.Frame(left, bg=row_bg,
                           highlightthickness=1, highlightbackground=PALETTE['separator'])
            row.pack(fill='x', pady=1)

            inner = tk.Frame(row, bg=row_bg)
            inner.pack(padx=6, pady=4)

            flag1 = get_flag(t1)
            if flag1:
                tk.Label(inner, image=flag1, bg=row_bg).pack(side='left', padx=(0, 4))
            tk.Label(inner, text=t1, bg=row_bg, fg=PALETTE['fg_main'],
                     font=('Segoe UI', 9), width=20, anchor='e').pack(side='left')

            gap = tk.Frame(inner, bg=row_bg)
            gap.pack(side='left', padx=8)

            e1 = _make_score_entry(gap, v1, self._on_score_change)
            e1.pack(side='left', padx=(0, 2))

            tk.Label(gap, text=':', bg=row_bg, fg=PALETTE['fg_main'],
                     font=('Segoe UI', 12, 'bold')).pack(side='left', padx=2)

            e2 = _make_score_entry(gap, v2, self._on_score_change)
            e2.pack(side='left', padx=(2, 0))

            tk.Label(inner, text=t2, bg=row_bg, fg=PALETTE['fg_main'],
                     font=('Segoe UI', 9), width=20, anchor='w').pack(side='left')
            flag2 = get_flag(t2)
            if flag2:
                tk.Label(inner, image=flag2, bg=row_bg).pack(side='left', padx=(4, 0))

        right = tk.Frame(body, bg=PALETTE['bg_card'])
        right.pack(side='left', anchor='n', fill='both', expand=True)

        tk.Label(right, text='Турнирная таблица', bg=PALETTE['bg_card'],
                 fg=PALETTE['fg_dim'], font=('Segoe UI', 9)).pack(anchor='w', pady=(0, 4))

        tbl_frame = tk.Frame(right, bg=PALETTE['bg_card'])
        tbl_frame.pack()

        # Заголовок таблицы
        hdr_row = tk.Frame(tbl_frame, bg=PALETTE['bg_header'])
        hdr_row.pack(fill='x', pady=(0, 1))
        headers = ['#', 'Команда', 'И', 'В', 'Н', 'П', 'ЗГ', 'ПГ', '+/−', 'О']
        widths = [30, 160, 30, 30, 30, 30, 35, 35, 40, 35]
        for col, (h, w) in enumerate(zip(headers, widths)):
            anchor = 'w' if col == 1 else 'center'
            tk.Label(hdr_row, text=h, bg=PALETTE['bg_header'], fg=PALETTE['fg_dim'],
                     font=('Segoe UI', 8, 'bold'), anchor=anchor, padx=3, pady=3, width=w//7).grid(
                row=0, column=col, padx=1)

        self._tbl_rows: list[list[tk.Label]] = []
        rank_bgs = [PALETTE['bg_rank1'], PALETTE['bg_rank2'], PALETTE['bg_rank3'], PALETTE['bg_rank4']]
        rank_fgs = [PALETTE['fg_green'], PALETTE['fg_green'], PALETTE['fg_yellow'], PALETTE['fg_dim']]

        self._tbl_body = tk.Frame(tbl_frame, bg=PALETTE['bg_card'])
        self._tbl_body.pack(fill='x')

        for rank in range(4):
            row_lbls = []
            rbg = rank_bgs[rank]
            rfg = rank_fgs[rank]
            for col, (h, w) in enumerate(zip(headers, widths)):
                anchor = 'w' if col == 1 else 'center'
                lbl = tk.Label(self._tbl_body, text='', bg=rbg,
                               fg=rfg, font=('Segoe UI', 9),
                               anchor=anchor, padx=3, pady=4, width=w//7)
                lbl.grid(row=rank, column=col, padx=1, pady=1, sticky='ew')
                row_lbls.append(lbl)
            self._tbl_rows.append(row_lbls)

        leg = tk.Frame(right, bg=PALETTE['bg_card'])
        leg.pack(anchor='w', pady=(4, 0))
        tk.Label(leg, text='■', fg=PALETTE['fg_green'], bg=PALETTE['bg_card'],
                 font=('Segoe UI', 8)).pack(side='left')
        tk.Label(leg, text=' Выход в плейофф  ', fg=PALETTE['fg_dim'], bg=PALETTE['bg_card'],
                 font=('Segoe UI', 8)).pack(side='left')
        tk.Label(leg, text='■', fg=PALETTE['fg_yellow'], bg=PALETTE['bg_card'],
                 font=('Segoe UI', 8)).pack(side='left')
        tk.Label(leg, text=' Кандидат (3-е место)', fg=PALETTE['fg_dim'], bg=PALETTE['bg_card'],
                 font=('Segoe UI', 8)).pack(side='left')

        self._update_table()

    def _on_score_change(self):
        self._update_table()
        if self.on_change:
            self.on_change()

    def _current_scores(self) -> dict[tuple, tuple | None]:
        result = {}
        for (i, j), (v1, v2) in self.score_vars.items():
            try:
                s1 = int(v1.get() or '0')
                s2 = int(v2.get() or '0')
                if s1 < 0 or s2 < 0:
                    result[(i, j)] = None
                else:
                    result[(i, j)] = (s1, s2)
            except ValueError:
                result[(i, j)] = None
        return result

    def _update_table(self):
        g = Group(self.group_name, self.teams)
        scores = self._current_scores()
        for (i, j), score in scores.items():
            if score is not None:
                g.set_result(self.teams[i], self.teams[j], score[0], score[1])

        table = g.standings()
        for rank, s in enumerate(table):
            diff_str = ('+' if s.goal_diff > 0 else '') + str(s.goal_diff)
            values = [str(rank + 1), s.team, str(s.played), str(s.wins),
                      str(s.draws), str(s.losses), str(s.goals_for),
                      str(s.goals_against), diff_str, str(s.points)]
            for col, val in enumerate(values):
                if col < len(self._tbl_rows[rank]):
                    self._tbl_rows[rank][col].configure(text=val)

    def is_complete(self) -> bool:
        scores = self._current_scores()
        return all(v is not None for v in scores.values())

    def get_group_for_tournament(self) -> Group | None:
        g = Group(self.group_name, self.teams)
        scores = self._current_scores()
        for (i, j), score in scores.items():
            if score is None:
                return None
            g.set_result(self.teams[i], self.teams[j], score[0], score[1])
        return g

    def reset(self):
        for v1, v2 in self.score_vars.values():
            v1.set('0')
            v2.set('0')

    def set_score(self, i: int, j: int, score1: int, score2: int):
        """
        Программно устанавливает счёт матча между командами с индексами
        i и j (в порядке, использованном при создании группы), не вызывая
        on_change на каждый отдельный вызов — используется при массовой
        загрузке реальных результатов (см. apply_real_results).
        """
        key = (i, j) if (i, j) in self.score_vars else (j, i)
        if key not in self.score_vars:
            return
        v1, v2 = self.score_vars[key]
        if key == (i, j):
            v1.set(str(score1))
            v2.set(str(score2))
        else:
            v1.set(str(score2))
            v2.set(str(score1))

    def apply_real_results(self, results: dict) -> int:
        """
        Применяет словарь {(i, j): (score1, score2)} к этой группе.
        Возвращает количество фактически изменённых матчей.
        """
        applied = 0
        for (i, j), (s1, s2) in results.items():
            self.set_score(i, j, s1, s2)
            applied += 1
        if applied:
            self._update_table()
        return applied


class ExtendedGroupsTab(tk.Frame):
    """
    Вкладка "Группы (расширенные)": ввод счётов всех 6 матчей round robin
    для каждой из 12 групп, с live-пересчётом турнирной таблицы.

    Фон вкладки оформлен как футбольное поле сверху (трава + декоративные
    полосы разметки между рядами карточек групп), см. pitch_theme.
    """

    def __init__(self, master, groups_data: dict[str, list[str]], on_change=None,
                 *args, **kwargs):
        super().__init__(master, bg=pitch_theme.GRASS_DARK, *args, **kwargs)
        self.groups_data = groups_data
        self.on_change = on_change
        self._ext_blocks: dict[str, GroupBlockExtended] = {}
        self._col_count = 2
        self._band_top: pitch_theme.PitchBand | None = None
        self._band_center: pitch_theme.PitchBand | None = None
        self._band_bottom: pitch_theme.PitchBand | None = None
        self._build_ui()

    def _build_ui(self):
        toolbar = tk.Frame(self, bg=PALETTE['bg_header'], pady=5)
        toolbar.pack(side='top', fill='x')

        tk.Label(toolbar, text='  ЧМ 2026  •  Расширенный режим (счёты матчей)',
                 bg=PALETTE['bg_header'], fg=PALETTE['fg_accent'],
                 font=('Segoe UI', 10, 'bold')).pack(side='left')

        self._ext_status = tk.Label(toolbar, text='', bg=PALETTE['bg_header'],
                                     fg=PALETTE['fg_dim'], font=('Segoe UI', 9))
        self._ext_status.pack(side='left', padx=12)

        self._load_real_btn = tk.Button(
            toolbar, text='⬇  Загрузить реальные результаты',
            bg=PALETTE['btn_bg'] if 'btn_bg' in PALETTE else '#2979ff',
            fg='white', relief='flat',
            font=('Segoe UI', 9, 'bold'), padx=10, pady=3,
            activebackground=PALETTE.get('btn_hover', '#448aff'),
            cursor='hand2', command=self._load_real_results
        )
        self._load_real_btn.pack(side='right', padx=(0, 6))

        reset_btn = tk.Button(
            toolbar, text='↺  Сбросить всё',
            bg=PALETTE['bg_card'], fg=PALETTE['fg_main'], relief='flat',
            font=('Segoe UI', 9), padx=10, pady=3,
            activebackground=PALETTE['border'], activeforeground=PALETTE['fg_main'],
            cursor='hand2', command=self._ext_reset_all
        )
        reset_btn.pack(side='right', padx=10)

        # Фрейм для скролла (фон — травяное поле)
        scroll_frame = tk.Frame(self, bg=pitch_theme.GRASS_DARK)
        scroll_frame.pack(fill='both', expand=True)

        self.ext_canvas = tk.Canvas(scroll_frame, bg=pitch_theme.GRASS_DARK, highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(scroll_frame, orient='vertical', command=self.ext_canvas.yview)
        h_scrollbar = ttk.Scrollbar(scroll_frame, orient='horizontal', command=self.ext_canvas.xview)

        self.ext_canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.ext_canvas.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        scroll_frame.grid_rowconfigure(0, weight=1)
        scroll_frame.grid_columnconfigure(0, weight=1)

        # Внутренний фрейм
        self.ext_inner = tk.Frame(self.ext_canvas, bg=pitch_theme.GRASS_DARK)
        self.ext_canvas_window = self.ext_canvas.create_window((0, 0), window=self.ext_inner, anchor='nw')

        # Декоративные полосы разметки поля (создаются один раз, переразмещаются
        # в _update_ext_grid в зависимости от текущего числа колонок)
        self._band_top = pitch_theme.PitchBand(self.ext_inner, kind='goal_top')
        self._band_center = pitch_theme.PitchBand(self.ext_inner, kind='center')
        self._band_bottom = pitch_theme.PitchBand(self.ext_inner, kind='goal_bottom')

        # Создаём блоки групп
        for group_name, teams in self.groups_data.items():
            block = GroupBlockExtended(
                self.ext_inner, group_name, teams,
                on_change=self._notify_change
            )
            self._ext_blocks[group_name] = block

        # Обновляем расположение
        self.ext_inner.bind('<Configure>', self._on_ext_inner_configure)
        self.ext_canvas.bind('<Configure>', self._on_ext_canvas_configure)

        # Скролл мышкой.
        # bind_all с add='+' и проверкой _mouse_over_tab — чтобы обработчики
        # колеса разных вкладок не затирали друг друга и скроллилась только
        # вкладка под курсором.
        self._mouse_over_tab = False
        self.bind('<Enter>', lambda e: setattr(self, '_mouse_over_tab', True))
        self.bind('<Leave>', lambda e: setattr(self, '_mouse_over_tab', False))

        def on_mousewheel(event):
            if not self._mouse_over_tab:
                return
            self.ext_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        def on_shift_mousewheel(event):
            if not self._mouse_over_tab:
                return
            self.ext_canvas.xview_scroll(int(-1 * (event.delta / 120)), 'units')

        def on_linux_scroll(event, dx=0, dy=0):
            if not self._mouse_over_tab:
                return
            if dx:
                self.ext_canvas.xview_scroll(dx, 'units')
            if dy:
                self.ext_canvas.yview_scroll(dy, 'units')

        self.ext_canvas.bind_all('<MouseWheel>', on_mousewheel, add='+')
        self.ext_canvas.bind_all('<Shift-MouseWheel>', on_shift_mousewheel, add='+')
        self.ext_canvas.bind_all('<Button-4>', lambda e: on_linux_scroll(e, dy=-1), add='+')
        self.ext_canvas.bind_all('<Button-5>', lambda e: on_linux_scroll(e, dy=1), add='+')
        self.ext_canvas.bind_all('<Shift-Button-4>', lambda e: on_linux_scroll(e, dx=-1), add='+')
        self.ext_canvas.bind_all('<Shift-Button-5>', lambda e: on_linux_scroll(e, dx=1), add='+')

        self._update_ext_grid()
        self._ext_update_status()

    def _on_ext_inner_configure(self, event):
        pitch_theme.repaint(self.ext_canvas, orientation='vertical')

    def _on_ext_canvas_configure(self, event):
        self._update_ext_grid()
        pitch_theme.repaint(self.ext_canvas, orientation='vertical')

    def _update_ext_grid(self):
        if not self._ext_blocks:
            return

        canvas_width = self.ext_canvas.winfo_width()

        if canvas_width < 1100:
            new_cols = 1
        elif canvas_width < 2200:
            new_cols = 2
        elif canvas_width < 3200:
            new_cols = 3
        else:
            new_cols = 4

        needs_layout = (new_cols != self._col_count) or (not self._band_top.winfo_ismapped())

        if needs_layout:
            self._col_count = new_cols

            for c in range(self._col_count):
                self.ext_inner.grid_columnconfigure(c, weight=1)

            blocks = list(self._ext_blocks.items())
            total_rows = (len(blocks) + self._col_count - 1) // self._col_count
            mid_row = total_rows // 2

            self._band_top.grid(row=0, column=0, columnspan=self._col_count, sticky='ew')

            row_offset = 1
            for idx, (group_name, block) in enumerate(blocks):
                row, col = divmod(idx, self._col_count)
                grid_row = row + row_offset + (1 if row >= mid_row else 0)
                if row == mid_row and idx % self._col_count == 0:
                    self._band_center.grid(row=grid_row - 1, column=0,
                                            columnspan=self._col_count, sticky='ew')
                block.grid(row=grid_row, column=col, padx=8, pady=6, sticky='nw')

            last_row = (total_rows - 1) + row_offset + (1 if (total_rows - 1) >= mid_row else 0)
            self._band_bottom.grid(row=last_row + 1, column=0,
                                    columnspan=self._col_count, sticky='ew')

            self.ext_inner.update_idletasks()
            pitch_theme.repaint(self.ext_canvas, orientation='vertical')

    def _notify_change(self):
        self._ext_update_status()
        if self.on_change:
            self.on_change()

    def _ext_update_status(self):
        complete = sum(1 for b in self._ext_blocks.values() if b.is_complete())
        total = len(self._ext_blocks)
        self._ext_status.configure(text=f'Групп с результатами: {complete} / {total}')

    def _ext_reset_all(self):
        for block in self._ext_blocks.values():
            block.reset()
        self._notify_change()

    def _load_real_results(self):
        """
        Запускает загрузку реальных результатов группового этапа в фоновом
        потоке (чтобы не подвешивать интерфейс на время сетевого запроса),
        затем применяет их к соответствующим полям счёта в GUI-потоке.
        """
        self._load_real_btn.configure(state='disabled', text='⏳  Загрузка…')

        def worker():
            try:
                results = live_data.get_real_results(self.groups_data)
            except live_data.LiveDataError as e:
                self.after(0, lambda: self._on_load_real_error(str(e)))
                return
            except Exception as e:  # неожиданная ошибка — не даём потоку умереть тихо
                self.after(0, lambda: self._on_load_real_error(f'Непредвиденная ошибка: {e}'))
                return
            self.after(0, lambda: self._on_load_real_success(results))

        threading.Thread(target=worker, daemon=True).start()

    def _on_load_real_success(self, results: dict):
        self._load_real_btn.configure(state='normal', text='⬇  Загрузить реальные результаты')

        total_applied = 0
        groups_touched = 0
        for group_name, matches in results.items():
            if not matches:
                continue
            block = self._ext_blocks.get(group_name)
            if block is None:
                continue
            applied = block.apply_real_results(matches)
            if applied:
                total_applied += applied
                groups_touched += 1

        self._notify_change()

        if total_applied == 0:
            messagebox.showinfo(
                'Реальные результаты',
                'На данный момент источник не сообщает результатов ни по одному '
                'сыгранному матчу группового этапа (возможно, матчи ещё не начались, '
                'либо источник обновляется с задержкой).'
            )
        else:
            messagebox.showinfo(
                'Реальные результаты загружены',
                f'Обновлено {total_applied} матч(ей) в {groups_touched} групп(ах).\n'
                'Поля, по которым у источника пока нет данных, не изменены.'
            )

    def _on_load_real_error(self, message: str):
        self._load_real_btn.configure(state='normal', text='⬇  Загрузить реальные результаты')
        messagebox.showerror('Не удалось загрузить результаты', message)

    def is_complete(self) -> bool:
        return all(b.is_complete() for b in self._ext_blocks.values())

    def get_group_result(self, group_name: str):
        """
        Возвращает заполненный group_stage.Group для указанной группы,
        если на этой вкладке введены все 6 результатов матчей; иначе None.
        """
        block = self._ext_blocks.get(group_name)
        if block is None:
            return None
        return block.get_group_for_tournament()

    def build_tournament(self) -> Tournament | None:
        if not self.is_complete():
            return None

        tournament = Tournament(self.groups_data)
        for group_name, block in self._ext_blocks.items():
            g_src = block.get_group_for_tournament()
            if g_src is None:
                return None
            g_dst = tournament.groups[group_name]
            for m in g_src.matches:
                if m.played:
                    g_dst.set_result(m.team1, m.team2, m.score1, m.score2)

        return tournament


if __name__ == '__main__':
    from data import GROUPS

    root = tk.Tk()
    root.title('Тест: расширенная вкладка групп ЧМ-2026')
    root.geometry('1300x850')

    def on_change():
        print('Изменение в расширенной вкладке')

    tab = ExtendedGroupsTab(root, GROUPS, on_change=on_change)
    tab.pack(fill='both', expand=True)

    root.mainloop()
