"""
GUI вкладки "Группы" — расширенная версия с вводом счётов матчей.

GroupBlockExtended показывает все 6 матчей round robin для группы из 4 команд.
Для каждого матча — два Spinbox'а (счёт хозяина : счёт гостя).
Таблица группы пересчитывается live при каждом изменении счёта.

GroupsTab поддерживает два режима (через radiobutton вверху):
  - "Базовый"    — оригинальный drag-and-drop (GroupBlock, из groups_gui.py)
  - "Расширенный"— ввод счётов матчей (GroupBlockExtended, этот файл)

В расширенном режиме build_tournament() возвращает Tournament с реальными
результатами всех матчей.
"""

import tkinter as tk
from tkinter import ttk
from itertools import combinations

from group_stage import Tournament, Group


# ---------------------------------------------------------------------------
# Вспомогательный класс: блок одной группы в расширенном режиме
# ---------------------------------------------------------------------------

MATCH_PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]  # round-robin 4 teams

STANDINGS_HEADERS = ['#', 'Команда', 'И', 'В', 'Н', 'П', 'ЗГ', 'ПГ', '+/-', 'О']
STANDINGS_COL_WIDTHS = [20, 140, 25, 25, 25, 25, 30, 30, 35, 28]


class GroupBlockExtended(ttk.Frame):
    """
    Визуальный блок одной группы: слева — 6 матчей с полями счёта,
    справа — live-таблица итоговых мест.
    """

    def __init__(self, master, group_name: str, teams: list[str], on_change=None, **kwargs):
        super().__init__(master, relief='ridge', borderwidth=1, padding=8, **kwargs)
        self.group_name = group_name
        self.teams = teams
        self.on_change = on_change

        # Переменные для каждого матча: (score1_var, score2_var)
        self.score_vars: dict[tuple, tuple] = {}  # (i, j) -> (IntVar, IntVar)

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        title = ttk.Label(self, text=f'Группа {self.group_name}',
                          font=('TkDefaultFont', 11, 'bold'))
        title.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 6))

        # Левая часть — матчи
        matches_outer = ttk.LabelFrame(self, text='Матчи', padding=4)
        matches_outer.grid(row=1, column=0, sticky='nw', padx=(0, 16))

        for row_idx, (i, j) in enumerate(MATCH_PAIRS):
            t1 = self.teams[i]
            t2 = self.teams[j]

            v1 = tk.IntVar(value=0)
            v2 = tk.IntVar(value=0)
            self.score_vars[(i, j)] = (v1, v2)

            # Callback при изменении любого счёта
            trace_cb = lambda *_, grp=self.group_name: self._on_score_change()
            v1.trace_add('write', trace_cb)
            v2.trace_add('write', trace_cb)

            row_frame = ttk.Frame(matches_outer)
            row_frame.grid(row=row_idx, column=0, sticky='w', pady=1)

            # Название команды 1 (фиксированная ширина)
            ttk.Label(row_frame, text=t1, width=22, anchor='e').pack(side='left', padx=(0, 4))

            sb1 = ttk.Spinbox(row_frame, from_=0, to=99, textvariable=v1,
                               width=3, justify='center')
            sb1.pack(side='left')

            ttk.Label(row_frame, text=':', width=2, anchor='center').pack(side='left')

            sb2 = ttk.Spinbox(row_frame, from_=0, to=99, textvariable=v2,
                               width=3, justify='center')
            sb2.pack(side='left')

            ttk.Label(row_frame, text=t2, width=22, anchor='w').pack(side='left', padx=(4, 0))

        # Правая часть — таблица группы
        table_outer = ttk.LabelFrame(self, text='Турнирная таблица', padding=4)
        table_outer.grid(row=1, column=1, sticky='nw')

        # Заголовок таблицы
        header_frame = ttk.Frame(table_outer)
        header_frame.pack(anchor='w')
        for col, (h, w) in enumerate(zip(STANDINGS_HEADERS, STANDINGS_COL_WIDTHS)):
            ttk.Label(header_frame, text=h, width=None, anchor='center',
                      font=('TkDefaultFont', 9, 'bold'),
                      foreground='#333').grid(row=0, column=col, padx=1)
            header_frame.columnconfigure(col, minsize=w)

        # Строки таблицы (4 команды)
        self.row_labels: list[list[tk.Label]] = []
        for rank in range(4):
            row_lbls = []
            for col in range(len(STANDINGS_HEADERS)):
                lbl = tk.Label(table_outer, text='', anchor='center',
                               font=('TkDefaultFont', 9),
                               bg='#f8f8f8', relief='flat', padx=2)
                lbl.pack_forget()
                row_lbls.append(lbl)
            self.row_labels.append(row_lbls)

        # Строки через grid внутри отдельного фрейма
        self.table_rows_frame = ttk.Frame(table_outer)
        self.table_rows_frame.pack(anchor='w')

        self._rebuild_table_rows()
        self._update_table()

    def _rebuild_table_rows(self):
        for widget in self.table_rows_frame.winfo_children():
            widget.destroy()
        self.row_labels = []
        for rank in range(4):
            row_lbls = []
            for col, (h, w) in enumerate(zip(STANDINGS_HEADERS, STANDINGS_COL_WIDTHS)):
                bg = '#e6f4ea' if rank < 2 else ('#fff7e0' if rank == 2 else '#f8f8f8')
                anchor = 'w' if col == 1 else 'center'
                lbl = tk.Label(self.table_rows_frame, text='', anchor=anchor,
                               font=('TkDefaultFont', 9), bg=bg, relief='flat',
                               padx=3, pady=2)
                lbl.grid(row=rank, column=col, padx=1, pady=1, sticky='ew')
                self.table_rows_frame.columnconfigure(col, minsize=w)
                row_lbls.append(lbl)
            self.row_labels.append(row_lbls)

    # ------------------------------------------------------------------
    def _on_score_change(self):
        self._update_table()
        if self.on_change:
            self.on_change()

    def _current_scores(self) -> dict[tuple, tuple | None]:
        """Возвращает {(i,j): (score1, score2)} — None если хотя бы одно поле пустое."""
        result = {}
        for (i, j), (v1, v2) in self.score_vars.items():
            try:
                s1 = int(v1.get())
                s2 = int(v2.get())
                result[(i, j)] = (s1, s2)
            except (tk.TclError, ValueError):
                result[(i, j)] = None
        return result

    def _update_table(self):
        """Пересчитывает таблицу по текущим счётам и обновляет метки."""
        # Строим временную группу и проставляем результаты
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
                self.row_labels[rank][col].configure(text=val)

    # ------------------------------------------------------------------
    def is_complete(self) -> bool:
        """Все 6 матчей имеют корректные счета."""
        scores = self._current_scores()
        return all(v is not None for v in scores.values())

    def get_group_for_tournament(self) -> Group | None:
        """Возвращает объект Group с проставленными результатами, или None если не все матчи заполнены."""
        g = Group(self.group_name, self.teams)
        scores = self._current_scores()
        for (i, j), score in scores.items():
            if score is None:
                return None
            g.set_result(self.teams[i], self.teams[j], score[0], score[1])
        return g

    def reset(self):
        """Сбрасывает все счета в 0."""
        for v1, v2 in self.score_vars.values():
            v1.set(0)
            v2.set(0)


# ---------------------------------------------------------------------------
# Полная вкладка "Группы" с переключением режимов
# ---------------------------------------------------------------------------

# Импортируем оригинальные классы базового режима
from groups_gui import GroupBlock, GroupsTab as _BaseGroupsTab


class GroupsTab(ttk.Frame):
    """
    Вкладка с 12 группами. Поддерживает два режима:
      mode='basic'    — оригинальный drag-and-drop по местам
      mode='extended' — ввод счётов всех матчей round robin
    """

    def __init__(self, master, groups_data: dict[str, list[str]], on_change=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.groups_data = groups_data
        self.on_change = on_change

        self.mode = tk.StringVar(value='basic')

        # Блоки обоих режимов (создаём оба, скрываем неактивный)
        self._basic_tab: _BaseGroupsTab | None = None
        self._ext_blocks: dict[str, GroupBlockExtended] = {}
        self._ext_canvas = None
        self._ext_inner = None
        self._ext_inner_id = None
        self._ext_scroll_frame = None

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        # Верхняя панель с переключателем режима
        top_bar = ttk.Frame(self)
        top_bar.pack(side='top', fill='x', padx=10, pady=6)

        ttk.Label(top_bar, text='Режим:', font=('TkDefaultFont', 10, 'bold')).pack(side='left')
        rb_basic = ttk.Radiobutton(
            top_bar, text='Базовый (расстановка по местам)',
            variable=self.mode, value='basic', command=self._on_mode_change
        )
        rb_basic.pack(side='left', padx=(8, 0))

        rb_ext = ttk.Radiobutton(
            top_bar, text='Расширенный (ввод счётов матчей)',
            variable=self.mode, value='extended', command=self._on_mode_change
        )
        rb_ext.pack(side='left', padx=(16, 0))

        # Контейнер, который мы будем переключать
        self._mode_container = ttk.Frame(self)
        self._mode_container.pack(side='top', fill='both', expand=True)

        # Строим оба режима
        self._build_basic_view()
        self._build_extended_view()

        # Показываем базовый по умолчанию
        self._show_basic()

    # ------------------------------------------------------------------
    def _build_basic_view(self):
        """Создаёт внутри _mode_container фрейм для базового режима."""
        self._basic_frame = ttk.Frame(self._mode_container)
        self._basic_tab = _BaseGroupsTab(
            self._basic_frame, self.groups_data,
            on_change=self._notify_change
        )
        self._basic_tab.pack(fill='both', expand=True)

    def _build_extended_view(self):
        """Создаёт прокручиваемый фрейм с GroupBlockExtended для каждой группы."""
        self._ext_frame = ttk.Frame(self._mode_container)

        # Верхняя панель кнопок расширенного режима
        ext_top = ttk.Frame(self._ext_frame)
        ext_top.pack(side='top', fill='x', padx=10, pady=4)

        ttk.Label(
            ext_top,
            text='Введите счёт каждого матча. Таблица пересчитывается автоматически.',
        ).pack(side='left')

        self._ext_status = ttk.Label(ext_top, text='')
        self._ext_status.pack(side='left', padx=16)

        ttk.Button(ext_top, text='Сбросить всё', command=self._ext_reset_all).pack(side='right')

        # Прокручиваемая область
        canvas_frame = ttk.Frame(self._ext_frame)
        canvas_frame.pack(side='top', fill='both', expand=True)

        self._ext_canvas = tk.Canvas(canvas_frame, borderwidth=0, highlightthickness=0)
        v_scroll = ttk.Scrollbar(canvas_frame, orient='vertical', command=self._ext_canvas.yview)
        self._ext_canvas.configure(yscrollcommand=v_scroll.set)

        self._ext_canvas.pack(side='left', fill='both', expand=True)
        v_scroll.pack(side='right', fill='y')

        self._ext_inner = ttk.Frame(self._ext_canvas)
        self._ext_inner_id = self._ext_canvas.create_window((0, 0), window=self._ext_inner, anchor='nw')

        self._ext_inner.bind('<Configure>', self._ext_on_inner_configure)
        self._ext_canvas.bind('<Configure>', self._ext_on_canvas_resize)
        self._ext_canvas.bind_all('<MouseWheel>', self._ext_on_mousewheel)
        self._ext_canvas.bind_all('<Button-4>', self._ext_on_mw_linux)
        self._ext_canvas.bind_all('<Button-5>', self._ext_on_mw_linux)

        for group_name, teams in self.groups_data.items():
            block = GroupBlockExtended(
                self._ext_inner, group_name, teams,
                on_change=self._notify_change
            )
            block.pack(fill='x', padx=10, pady=6)
            self._ext_blocks[group_name] = block

        self._ext_update_status()

    def _ext_on_inner_configure(self, event):
        self._ext_canvas.configure(scrollregion=self._ext_canvas.bbox('all'))

    def _ext_on_canvas_resize(self, event):
        self._ext_canvas.itemconfigure(self._ext_inner_id, width=event.width)

    def _ext_on_mousewheel(self, event):
        if self.mode.get() == 'extended':
            self._ext_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def _ext_on_mw_linux(self, event):
        if self.mode.get() == 'extended':
            delta = -1 if event.num == 4 else 1
            self._ext_canvas.yview_scroll(delta, 'units')

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

    # ------------------------------------------------------------------
    def _notify_change(self):
        if self.mode.get() == 'extended':
            self._ext_update_status()
        if self.on_change:
            self.on_change()

    def _ext_update_status(self):
        complete = sum(1 for b in self._ext_blocks.values() if b.is_complete())
        total = len(self._ext_blocks)
        self._ext_status.configure(text=f'Заполнено групп: {complete} / {total}')

    def _ext_reset_all(self):
        for block in self._ext_blocks.values():
            block.reset()
        self._notify_change()

    # ------------------------------------------------------------------
    # Публичный API (совпадает с оригинальным GroupsTab)
    # ------------------------------------------------------------------

    def is_complete(self) -> bool:
        if self.mode.get() == 'basic':
            return self._basic_tab.is_complete()
        return all(b.is_complete() for b in self._ext_blocks.values())

    def build_tournament(self) -> Tournament | None:
        """Строит Tournament из текущего состояния активного режима."""
        if self.mode.get() == 'basic':
            return self._basic_tab.build_tournament()

        # Расширенный режим — используем реальные счета
        if not self.is_complete():
            return None

        groups_for_tournament = {name: teams for name, teams in self.groups_data.items()}
        tournament = Tournament(groups_for_tournament)

        for group_name, block in self._ext_blocks.items():
            g_src = block.get_group_for_tournament()
            if g_src is None:
                return None
            g_dst = tournament.groups[group_name]
            for m in g_src.matches:
                if m.played:
                    g_dst.set_result(m.team1, m.team2, m.score1, m.score2)

        return tournament


