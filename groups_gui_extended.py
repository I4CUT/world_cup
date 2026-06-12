"""
GUI вкладки "Группы" — расширенная версия с вводом счётов матчей.

Два режима переключаются radiobutton-ами вверху вкладки:
  - "Базовый"    — drag-and-drop по местам (groups_gui.GroupsTab)
  - "Расширенный"— ввод счётов всех 6 матчей round robin

Расширенный режим:
  • Для каждого матча — два поля Entry (только целые ≥ 0)
  • Таблица группы пересчитывается live
  • Флаги стран рядом с названиями команд

Флаги загружаются из ./flags_png/{iso}.png (32x24 px).
Путь к папке флагов: FLAGS_DIR (см. ниже).
"""

import tkinter as tk
from tkinter import ttk
import os
from pathlib import Path
from itertools import combinations

from group_stage import Tournament, Group
from groups_gui import GroupBlock, GroupsTab as _BaseGroupsTab

# ------------------------------------------------------------------
# Пути к флагам (рядом с этим файлом или в подпапке flags_png/)
# ------------------------------------------------------------------
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

# Кэш PhotoImage (глобальный, иначе сборщик мусора уничтожит изображения)
_FLAG_CACHE: dict[str, tk.PhotoImage] = {}


def get_flag(team: str) -> tk.PhotoImage | None:
    """Возвращает PhotoImage флага команды или None."""
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


# ------------------------------------------------------------------
# Современная цветовая палитра
# ------------------------------------------------------------------
PALETTE = {
    'bg_main':    '#1a1f2e',   # тёмный фон
    'bg_card':    '#242938',   # карточка группы
    'bg_header':  '#2d3349',   # заголовок карточки
    'bg_match':   '#1e2336',   # строка матча
    'bg_match_alt': '#212640', # чередующийся фон
    'bg_table':   '#1e2336',
    'bg_rank1':   '#1a3a2a',   # 1–2 место (тёмно-зелёный)
    'bg_rank2':   '#1a3a2a',
    'bg_rank3':   '#3a3010',   # 3-е место (жёлтый)
    'bg_rank4':   '#2a1a1a',   # 4-е место (красноватый)
    'fg_main':    '#e8eaf0',
    'fg_dim':     '#8892aa',
    'fg_accent':  '#4fc3f7',   # голубой акцент
    'fg_green':   '#69f0ae',
    'fg_yellow':  '#ffd740',
    'border':     '#363d56',
    'entry_bg':   '#2d3349',
    'entry_fg':   '#ffffff',
    'entry_border':'#4fc3f7',
    'btn_bg':     '#2979ff',
    'btn_hover':  '#448aff',
    'separator':  '#363d56',
}

MATCH_PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]

STANDINGS_HEADERS = ['#', 'Команда', 'И', 'В', 'Н', 'П', 'ЗГ', 'ПГ', '+/−', 'О']
STANDINGS_COL_W   = [22, 160, 28, 28, 28, 28, 32, 32, 38, 32]


# ------------------------------------------------------------------
# Валидированный Entry (только целые ≥ 0)
# ------------------------------------------------------------------

def _make_score_entry(parent, textvariable, on_change_cb, palette=PALETTE) -> tk.Entry:
    """Создаёт Entry с валидацией (только целые ≥ 0)."""
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
        bg=palette['entry_bg'],
        fg=palette['entry_fg'],
        insertbackground=palette['entry_fg'],
        relief='flat',
        highlightthickness=2,
        highlightbackground=palette['border'],
        highlightcolor=palette['entry_border'],
    )
    textvariable.trace_add('write', lambda *_: on_change_cb())
    return entry


# ------------------------------------------------------------------
# Блок одной группы — расширенный режим
# ------------------------------------------------------------------

class GroupBlockExtended(tk.Frame):
    def __init__(self, master, group_name: str, teams: list[str], on_change=None, **kwargs):
        p = PALETTE
        super().__init__(master, bg=p['bg_card'],
                         highlightthickness=1, highlightbackground=p['border'],
                         **kwargs)
        self.group_name = group_name
        self.teams = teams
        self.on_change = on_change
        self.score_vars: dict[tuple, tuple] = {}  # (i,j) -> (StringVar, StringVar)
        self._build_ui()

    def _build_ui(self):
        p = PALETTE
        # Заголовок карточки
        hdr = tk.Frame(self, bg=p['bg_header'])
        hdr.pack(fill='x')
        tk.Label(hdr, text=f'  ГРУППА  {self.group_name}',
                 bg=p['bg_header'], fg=p['fg_accent'],
                 font=('Segoe UI', 11, 'bold'), pady=6).pack(side='left')

        body = tk.Frame(self, bg=p['bg_card'])
        body.pack(fill='both', padx=8, pady=6)

        # ---- левая колонка: матчи ----
        left = tk.Frame(body, bg=p['bg_card'])
        left.pack(side='left', anchor='n', padx=(0, 16))

        tk.Label(left, text='Матчи', bg=p['bg_card'],
                 fg=p['fg_dim'], font=('Segoe UI', 9)).pack(anchor='w', pady=(0, 4))

        for idx, (i, j) in enumerate(MATCH_PAIRS):
            t1, t2 = self.teams[i], self.teams[j]
            v1, v2 = tk.StringVar(value='0'), tk.StringVar(value='0')
            self.score_vars[(i, j)] = (v1, v2)

            row_bg = p['bg_match'] if idx % 2 == 0 else p['bg_match_alt']
            row = tk.Frame(left, bg=row_bg,
                           highlightthickness=1, highlightbackground=p['separator'])
            row.pack(fill='x', pady=1)

            inner = tk.Frame(row, bg=row_bg)
            inner.pack(padx=6, pady=4)

            # команда 1
            flag1 = get_flag(t1)
            if flag1:
                tk.Label(inner, image=flag1, bg=row_bg).pack(side='left', padx=(0, 4))
            tk.Label(inner, text=t1, bg=row_bg, fg=p['fg_main'],
                     font=('Segoe UI', 9), width=22, anchor='e').pack(side='left')

            # разделитель + поля счёта
            gap = tk.Frame(inner, bg=row_bg)
            gap.pack(side='left', padx=8)

            e1 = _make_score_entry(gap, v1, self._on_score_change)
            e1.pack(side='left', padx=(0, 2))

            tk.Label(gap, text=':', bg=row_bg, fg=p['fg_main'],
                     font=('Segoe UI', 12, 'bold')).pack(side='left', padx=2)

            e2 = _make_score_entry(gap, v2, self._on_score_change)
            e2.pack(side='left', padx=(2, 0))

            # команда 2
            tk.Label(inner, text=t2, bg=row_bg, fg=p['fg_main'],
                     font=('Segoe UI', 9), width=22, anchor='w').pack(side='left')
            flag2 = get_flag(t2)
            if flag2:
                tk.Label(inner, image=flag2, bg=row_bg).pack(side='left', padx=(4, 0))

        # ---- правая колонка: турнирная таблица ----
        right = tk.Frame(body, bg=p['bg_card'])
        right.pack(side='left', anchor='n')

        tk.Label(right, text='Турнирная таблица', bg=p['bg_card'],
                 fg=p['fg_dim'], font=('Segoe UI', 9)).pack(anchor='w', pady=(0, 4))

        tbl_frame = tk.Frame(right, bg=p['bg_card'])
        tbl_frame.pack()

        # Заголовок таблицы
        hdr_row = tk.Frame(tbl_frame, bg=p['bg_header'])
        hdr_row.pack(fill='x', pady=(0, 1))
        for col, (h, w) in enumerate(zip(STANDINGS_HEADERS, STANDINGS_COL_W)):
            anchor = 'w' if col == 1 else 'center'
            tk.Label(hdr_row, text=h, bg=p['bg_header'], fg=p['fg_dim'],
                     font=('Segoe UI', 8, 'bold'), width=None,
                     anchor=anchor, padx=3, pady=3).grid(
                row=0, column=col, padx=1)
            hdr_row.columnconfigure(col, minsize=w)

        # Строки таблицы
        self._tbl_rows: list[list[tk.Label]] = []
        rank_bgs = [p['bg_rank1'], p['bg_rank2'], p['bg_rank3'], p['bg_rank4']]
        rank_fgs = [p['fg_green'], p['fg_green'], p['fg_yellow'], p['fg_dim']]

        self._tbl_body = tk.Frame(tbl_frame, bg=p['bg_card'])
        self._tbl_body.pack(fill='x')

        for rank in range(4):
            row_lbls = []
            rbg = rank_bgs[rank]
            rfg = rank_fgs[rank]
            for col, (h, w) in enumerate(zip(STANDINGS_HEADERS, STANDINGS_COL_W)):
                anchor = 'w' if col == 1 else 'center'
                lbl = tk.Label(self._tbl_body, text='', bg=rbg,
                               fg=rfg, font=('Segoe UI', 9),
                               anchor=anchor, padx=3, pady=4)
                lbl.grid(row=rank, column=col, padx=1, pady=1, sticky='ew')
                self._tbl_body.columnconfigure(col, minsize=w)
                row_lbls.append(lbl)
            self._tbl_rows.append(row_lbls)

        # Легенда
        leg = tk.Frame(right, bg=p['bg_card'])
        leg.pack(anchor='w', pady=(4, 0))
        tk.Label(leg, text='■', fg=p['fg_green'], bg=p['bg_card'],
                 font=('Segoe UI', 8)).pack(side='left')
        tk.Label(leg, text=' Выход в плейофф  ', fg=p['fg_dim'], bg=p['bg_card'],
                 font=('Segoe UI', 8)).pack(side='left')
        tk.Label(leg, text='■', fg=p['fg_yellow'], bg=p['bg_card'],
                 font=('Segoe UI', 8)).pack(side='left')
        tk.Label(leg, text=' Кандидат (3-е место)', fg=p['fg_dim'], bg=p['bg_card'],
                 font=('Segoe UI', 8)).pack(side='left')

        self._update_table()

    # ------------------------------------------------------------------
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
                self._tbl_rows[rank][col].configure(text=val)

    # ------------------------------------------------------------------
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


# ------------------------------------------------------------------
# Вкладка "Группы" с переключателем режимов
# ------------------------------------------------------------------

class GroupsTab(tk.Frame):
    def __init__(self, master, groups_data: dict[str, list[str]], on_change=None, *args, **kwargs):
        p = PALETTE
        super().__init__(master, bg=p['bg_main'], *args, **kwargs)
        self.groups_data = groups_data
        self.on_change = on_change
        self.mode = tk.StringVar(value='extended')
        self._ext_blocks: dict[str, GroupBlockExtended] = {}
        self._basic_tab_widget = None
        self._build_ui()

    def _build_ui(self):
        p = PALETTE

        # Top bar
        top = tk.Frame(self, bg=p['bg_header'], pady=6)
        top.pack(side='top', fill='x')

        tk.Label(top, text='  ЧМ 2026  •  Режим:', bg=p['bg_header'],
                 fg=p['fg_accent'], font=('Segoe UI', 10, 'bold')).pack(side='left')

        style = ttk.Style()
        style.configure('Mode.TRadiobutton',
                        background=p['bg_header'],
                        foreground=p['fg_main'],
                        font=('Segoe UI', 10))

        rb_ext = ttk.Radiobutton(top, text='Расширенный (счёты матчей)',
                                  variable=self.mode, value='extended',
                                  command=self._on_mode_change, style='Mode.TRadiobutton')
        rb_ext.pack(side='left', padx=(12, 0))

        rb_basic = ttk.Radiobutton(top, text='Базовый (расстановка по местам)',
                                    variable=self.mode, value='basic',
                                    command=self._on_mode_change, style='Mode.TRadiobutton')
        rb_basic.pack(side='left', padx=(16, 0))

        self._mode_container = tk.Frame(self, bg=p['bg_main'])
        self._mode_container.pack(fill='both', expand=True)

        self._build_extended_view()
        self._build_basic_view()
        self._show_extended()

    # ------------------------------------------------------------------
    def _build_basic_view(self):
        self._basic_frame = tk.Frame(self._mode_container, bg=PALETTE['bg_main'])
        self._basic_tab_widget = _BaseGroupsTab(
            self._basic_frame, self.groups_data,
            on_change=self._notify_change
        )
        self._basic_tab_widget.pack(fill='both', expand=True)

    def _build_extended_view(self):
        p = PALETTE
        self._ext_frame = tk.Frame(self._mode_container, bg=p['bg_main'])

        # Панель инструментов
        toolbar = tk.Frame(self._ext_frame, bg=p['bg_header'], pady=5)
        toolbar.pack(side='top', fill='x')

        self._ext_status = tk.Label(toolbar, text='', bg=p['bg_header'],
                                     fg=p['fg_dim'], font=('Segoe UI', 9))
        self._ext_status.pack(side='left', padx=12)

        reset_btn = tk.Button(
            toolbar, text='↺  Сбросить всё',
            bg=p['bg_card'], fg=p['fg_main'], relief='flat',
            font=('Segoe UI', 9), padx=10, pady=3,
            activebackground=p['border'], activeforeground=p['fg_main'],
            cursor='hand2', command=self._ext_reset_all
        )
        reset_btn.pack(side='right', padx=10)

        # Прокручиваемая область
        cf = tk.Frame(self._ext_frame, bg=p['bg_main'])
        cf.pack(fill='both', expand=True)

        self._ext_canvas = tk.Canvas(cf, bg=p['bg_main'],
                                      highlightthickness=0, borderwidth=0)
        vsb = ttk.Scrollbar(cf, orient='vertical', command=self._ext_canvas.yview)
        self._ext_canvas.configure(yscrollcommand=vsb.set)
        self._ext_canvas.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self._ext_inner = tk.Frame(self._ext_canvas, bg=p['bg_main'])
        self._ext_inner_id = self._ext_canvas.create_window(
            (0, 0), window=self._ext_inner, anchor='nw'
        )
        self._ext_inner.bind('<Configure>',
                              lambda e: self._ext_canvas.configure(
                                  scrollregion=self._ext_canvas.bbox('all')))
        self._ext_canvas.bind('<Configure>',
                               lambda e: self._ext_canvas.itemconfigure(
                                   self._ext_inner_id, width=e.width))

        self._ext_canvas.bind_all('<MouseWheel>',
            lambda e: self._ext_canvas.yview_scroll(int(-1*(e.delta/120)), 'units')
            if self.mode.get() == 'extended' else None)
        self._ext_canvas.bind_all('<Button-4>',
            lambda e: self._ext_canvas.yview_scroll(-1, 'units')
            if self.mode.get() == 'extended' else None)
        self._ext_canvas.bind_all('<Button-5>',
            lambda e: self._ext_canvas.yview_scroll(1, 'units')
            if self.mode.get() == 'extended' else None)

        # Сетка 3 колонки
        col_count = 3
        items = list(self.groups_data.items())
        for idx, (group_name, teams) in enumerate(items):
            block = GroupBlockExtended(
                self._ext_inner, group_name, teams,
                on_change=self._notify_change
            )
            row, col = divmod(idx, col_count)
            block.grid(row=row, column=col, padx=8, pady=6, sticky='nw')
            self._ext_blocks[group_name] = block

        self._ext_update_status()

    # ------------------------------------------------------------------
    def _on_mode_change(self):
        if self.mode.get() == 'basic':
            self._show_basic()
        else:
            self._show_extended()
        self._notify_change()

    def _show_basic(self):
        self._ext_frame.pack_forget()
        self._basic_frame.pack(fill='both', expand=True)

    def _show_extended(self):
        self._basic_frame.pack_forget()
        self._ext_frame.pack(fill='both', expand=True)

    def _notify_change(self):
        if self.mode.get() == 'extended':
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

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------
    def is_complete(self) -> bool:
        if self.mode.get() == 'basic':
            return self._basic_tab_widget.is_complete()
        return all(b.is_complete() for b in self._ext_blocks.values())

    def build_tournament(self) -> Tournament | None:
        if self.mode.get() == 'basic':
            return self._basic_tab_widget.build_tournament()

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
