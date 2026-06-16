"""
GUI вкладки "Группы" — базовая версия (улучшенный дизайн).

Для каждой из 12 групп показываются 4 команды, которые можно перетащить
мышью в 4 слота ("1 место" .. "4 место"). На основе итогового распределения
формируется Tournament с фиктивными результатами матчей, которые дают
ровно такую таблицу (1-е место - 9 очков, 2-е - 6, 3-е - 3, 4-е - 0,
без голов), чтобы bracket_logic мог построить сетку плейофф.

UI: сетка 3 колонки с вертикальной прокруткой.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk

from group_stage import Tournament

# Цветовая палитра (полная версия)
PALETTE = {
    'bg_main':      '#1a1f2e',   # тёмный фон
    'bg_card':      '#242938',   # карточка группы
    'bg_header':    '#2d3349',   # заголовок карточки
    'bg_slot':      '#1e2336',   # фон слота
    'bg_pool':      '#1e2336',   # фон пула
    'bg_match':     '#1e2336',   # фон строки матча
    'bg_match_alt': '#212640',   # чередующийся фон
    'bg_table':     '#1e2336',
    'bg_rank1':     '#1a3a2a',   # 1–2 место
    'bg_rank2':     '#1a3a2a',
    'bg_rank3':     '#3a3010',   # 3-е место
    'bg_rank4':     '#2a1a1a',   # 4-е место
    'fg_main':      '#e8eaf0',
    'fg_dim':       '#8892aa',
    'fg_accent':    '#4fc3f7',   # голубой акцент
    'fg_green':     '#69f0ae',
    'fg_yellow':    '#ffd740',
    'border':       '#363d56',
    'entry_bg':     '#2d3349',
    'entry_fg':     '#ffffff',
    'entry_border': '#4fc3f7',
    'slot_empty':   '#2a2f42',
    'separator':    '#363d56',
    'btn_bg':       '#2979ff',
    'btn_hover':    '#448aff',
    'winner_bg':    '#1a3a2a',
}

SLOT_LABELS = ['1 место', '2 место', '3 место', '4 место']

# Флаги стран
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


class DraggableLabel(tk.Frame):
    """Лейбл команды с флагом, который можно перетаскивать между контейнерами."""

    def __init__(self, master, text, controller, block=None, **kwargs):
        super().__init__(master, bg=PALETTE['entry_bg'], **kwargs)
        self.team = text
        self.controller = controller
        self.block = block
        self._drag_data = {'x': 0, 'y': 0, 'item': None}

        flag = get_flag(text)
        if flag:
            self.flag_lbl = tk.Label(self, image=flag, bg=PALETTE['entry_bg'])
            self.flag_lbl.image = flag  # keep reference
            self.flag_lbl.pack(side='left', padx=(6, 4), pady=2)

        self.text_lbl = tk.Label(self, text=text, relief='raised', borderwidth=1,
                                  padx=8, pady=4, cursor='hand2',
                                  bg=PALETTE['entry_bg'], fg=PALETTE['fg_main'],
                                  font=('Segoe UI', 9))
        self.text_lbl.pack(side='left', padx=(0, 6), pady=2)

        # Bind events to both the frame and inner labels
        for w in (self, self.text_lbl):
            w.bind('<ButtonPress-1>', self._on_press)
            w.bind('<B1-Motion>', self._on_motion)
            w.bind('<ButtonRelease-1>', self._on_release)
        if hasattr(self, 'flag_lbl'):
            self.flag_lbl.bind('<ButtonPress-1>', self._on_press)
            self.flag_lbl.bind('<B1-Motion>', self._on_motion)
            self.flag_lbl.bind('<ButtonRelease-1>', self._on_release)

    def _on_press(self, event):
        self._drag_data['x'] = event.x_root
        self._drag_data['y'] = event.y_root
        self.lift()
        self._floating = tk.Toplevel(self)
        self._floating.overrideredirect(True)
        self._floating.attributes('-alpha', 0.9)
        
        # Floating window also shows flag + text
        float_content = tk.Frame(self._floating, bg=PALETTE['fg_accent'])
        float_content.pack()
        flag = get_flag(self.team)
        if flag:
            fl = tk.Label(float_content, image=flag, bg=PALETTE['fg_accent'])
            fl.image = flag
            fl.pack(side='left', padx=(6, 4), pady=2)
        tk.Label(float_content, text=self.team, relief='raised',
                  borderwidth=1, padx=8, pady=4, bg=PALETTE['fg_accent'],
                  fg='white', font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(0, 6), pady=2)
        
        self._update_floating_pos(event)
        self.text_lbl.configure(bg=PALETTE['border'])
        if hasattr(self, 'flag_lbl'):
            self.flag_lbl.configure(bg=PALETTE['border'])

    def _on_motion(self, event):
        if getattr(self, '_floating', None):
            self._update_floating_pos(event)

    def _update_floating_pos(self, event):
        x = event.x_root + 5
        y = event.y_root + 5
        self._floating.geometry(f'+{x}+{y}')

    def _on_release(self, event):
        if getattr(self, '_floating', None):
            self._floating.destroy()
            self._floating = None
        self.text_lbl.configure(bg=PALETTE['entry_bg'])
        if hasattr(self, 'flag_lbl'):
            self.flag_lbl.configure(bg=PALETTE['entry_bg'])

        dx = abs(event.x_root - self._drag_data['x'])
        dy = abs(event.y_root - self._drag_data['y'])

        if dx < 4 and dy < 4:
            self.controller.handle_click(self)
            return

        widget = self.winfo_containing(event.x_root, event.y_root)
        target = self._find_drop_target(widget)
        if target is not None:
            self.controller.handle_drop(self, target)

    @staticmethod
    def _find_drop_target(widget):
        w = widget
        while w is not None:
            if isinstance(w, (SlotFrame, PoolFrame)):
                return w
            w = getattr(w, 'master', None)
        return None


class SlotFrame(tk.Frame):
    """Один слот ("1 место" и т.п.)."""

    def __init__(self, master, group_name: str, slot_index: int, label_text: str, **kwargs):
        super().__init__(master, bg=PALETTE['bg_slot'],
                         relief='solid', borderwidth=1,
                         highlightbackground=PALETTE['border'],
                         width=180, height=40, **kwargs)
        self.group_name = group_name
        self.slot_index = slot_index
        self.team_label = None

        self.placeholder = tk.Label(self, text=label_text, 
                                      bg=PALETTE['bg_slot'], fg=PALETTE['fg_dim'],
                                      font=('Segoe UI', 9, 'italic'))
        self.placeholder.pack(expand=True, fill='both')

        self.pack_propagate(False)

    def is_empty(self) -> bool:
        return self.team_label is None

    def set_team(self, label: DraggableLabel):
        self.placeholder.pack_forget()
        label.pack(in_=self, expand=True, fill='both')
        self.team_label = label

    def clear(self) -> DraggableLabel | None:
        old = self.team_label
        if old is not None:
            old.pack_forget()
            self.team_label = None
            self.placeholder.pack(expand=True, fill='both')
        return old


class PoolFrame(tk.Frame):
    """Контейнер нераспределённых команд группы."""

    def __init__(self, master, group_name: str, **kwargs):
        super().__init__(master, bg=PALETTE['bg_pool'],
                         relief='solid', borderwidth=1,
                         highlightbackground=PALETTE['border'],
                         **kwargs)
        self.group_name = group_name


class GroupBlock(tk.Frame):
    """Визуальный блок одной группы."""

    def __init__(self, master, group_name: str, teams: list[str], controller, **kwargs):
        super().__init__(master, bg=PALETTE['bg_card'],
                         relief='solid', borderwidth=1,
                         highlightbackground=PALETTE['border'],
                         padx=10, pady=8, **kwargs)
        self.group_name = group_name
        self.controller = controller

        # Заголовок
        title = tk.Label(self, text=f'ГРУППА {group_name}',
                         bg=PALETTE['bg_header'], fg=PALETTE['fg_accent'],
                         font=('Segoe UI', 11, 'bold'), pady=5)
        title.pack(fill='x', pady=(0, 8))

        # Основной контент
        content = tk.Frame(self, bg=PALETTE['bg_card'])
        content.pack(fill='x')

        # Пул команд (слева)
        pool_frame = tk.Frame(content, bg=PALETTE['bg_card'])
        pool_frame.pack(side='left', fill='x', expand=True)

        tk.Label(pool_frame, text='Команды (перетащите):',
                 bg=PALETTE['bg_card'], fg=PALETTE['fg_dim'],
                 font=('Segoe UI', 8)).pack(anchor='w', pady=(0, 4))

        self.pool = PoolFrame(pool_frame, group_name)
        self.pool.pack(fill='x', pady=(0, 5))

        # Слоты мест (справа)
        slots_frame = tk.Frame(content, bg=PALETTE['bg_card'])
        slots_frame.pack(side='right', padx=(20, 0))

        tk.Label(slots_frame, text='Итоговые места:',
                 bg=PALETTE['bg_card'], fg=PALETTE['fg_dim'],
                 font=('Segoe UI', 8)).pack(anchor='w', pady=(0, 4))

        self.slots: list[SlotFrame] = []
        colors = [PALETTE['fg_green'], PALETTE['fg_green'], 
                  PALETTE['fg_yellow'], PALETTE['fg_dim']]
        
        for i, label_text in enumerate(SLOT_LABELS):
            row = tk.Frame(slots_frame, bg=PALETTE['bg_card'])
            row.pack(fill='x', pady=2)
            
            color = colors[i] if i < len(colors) else PALETTE['fg_dim']
            tk.Label(row, text=label_text, width=12, anchor='w',
                     bg=PALETTE['bg_card'], fg=color,
                     font=('Segoe UI', 9, 'bold')).pack(side='left')
            
            slot = SlotFrame(row, group_name, i, '(пусто)')
            slot.pack(side='left')
            self.slots.append(slot)

        self.labels: dict[str, DraggableLabel] = {}
        for team in teams:
            lbl = DraggableLabel(self, team, controller, block=self)
            lbl.pack(in_=self.pool, pady=2, padx=4, fill='x')
            self.labels[team] = lbl

    def get_standings(self) -> list[str] | None:
        teams = []
        for slot in self.slots:
            if slot.team_label is None:
                return None
            teams.append(slot.team_label.team)
        return teams

    def reset(self):
        for slot in self.slots:
            label = slot.clear()
            if label is not None:
                label.pack(in_=self.pool, pady=2, padx=4, fill='x')


class GroupsTab(tk.Frame):
    """Вкладка с 12 группами в сетке 3 колонки."""

    def __init__(self, master, groups_data: dict[str, list[str]], on_change=None, *args, **kwargs):
        super().__init__(master, bg=PALETTE['bg_main'], *args, **kwargs)
        self.groups_data = groups_data
        self.on_change = on_change
        self.blocks: dict[str, GroupBlock] = {}

        self._build_ui()

    def _build_ui(self):
        top_bar = tk.Frame(self, bg=PALETTE['bg_header'], pady=6)
        top_bar.pack(side='top', fill='x')

        tk.Label(top_bar, text='  ЧМ 2026  •  Базовый режим (расстановка по местам)',
                 bg=PALETTE['bg_header'], fg=PALETTE['fg_accent'],
                 font=('Segoe UI', 10, 'bold')).pack(side='left')

        info_text = ('Перетащите команду в слот (1-4 место) или кликните по ней → '
                     'первый свободный слот. Клик по команде в слоте → вернуть в пул.')
        tk.Label(top_bar, text=info_text, bg=PALETTE['bg_header'],
                 fg=PALETTE['fg_dim'], font=('Segoe UI', 9)).pack(side='left', padx=20)

        reset_btn = tk.Button(top_bar, text='↺ Сбросить всё',
                               bg=PALETTE['bg_card'], fg=PALETTE['fg_main'],
                               relief='flat', font=('Segoe UI', 9), padx=10, pady=3,
                               activebackground=PALETTE['border'],
                               cursor='hand2', command=self.reset_all)
        reset_btn.pack(side='right', padx=10)

        self.status_label = tk.Label(top_bar, text='',
                                      bg=PALETTE['bg_header'], fg=PALETTE['fg_green'],
                                      font=('Segoe UI', 9, 'bold'))
        self.status_label.pack(side='right', padx=10)

        # Прокручиваемая область
        cf = tk.Frame(self, bg=PALETTE['bg_main'])
        cf.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(cf, bg=PALETTE['bg_main'],
                                 highlightthickness=0, borderwidth=0)
        vsb = ttk.Scrollbar(cf, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self.inner = tk.Frame(self.canvas, bg=PALETTE['bg_main'])
        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.inner.bind('<Configure>', self._on_configure)
        self.canvas.bind('<Configure>', self._on_canvas_resize)

        # Скролл колёсиком
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        
        def on_mousewheel_linux_up(event):
            self.canvas.yview_scroll(-1, 'units')
        
        def on_mousewheel_linux_down(event):
            self.canvas.yview_scroll(1, 'units')
        
        self.canvas.bind_all('<MouseWheel>', on_mousewheel)
        self.canvas.bind_all('<Button-4>', on_mousewheel_linux_up)
        self.canvas.bind_all('<Button-5>', on_mousewheel_linux_down)

        # Группы в сетке 3 колонки
        items = list(self.groups_data.items())
        col_count = 3
        for idx, (group_name, teams) in enumerate(items):
            block = GroupBlock(self.inner, group_name, teams, self)
            row, col = divmod(idx, col_count)
            block.grid(row=row, column=col, padx=8, pady=6, sticky='nw')
            self.blocks[group_name] = block

        self._update_status()

    def _on_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_resize(self, event):
        self.canvas.itemconfigure(self.inner_id, width=event.width)

    def _find_current_slot(self, block: GroupBlock, label: DraggableLabel) -> SlotFrame | None:
        for slot in block.slots:
            if slot.team_label is label:
                return slot
        return None

    def handle_click(self, label: DraggableLabel):
        block = label.block
        if block is None:
            return

        current_slot = self._find_current_slot(block, label)

        if current_slot is None:
            for slot in block.slots:
                if slot.team_label is None:
                    label.pack_forget()
                    slot.set_team(label)
                    break
        else:
            current_slot.clear()
            label.pack_forget()
            label.pack(in_=block.pool, pady=2, padx=4, fill='x')

        self._update_status()
        if self.on_change:
            self.on_change()

    def handle_drop(self, label: DraggableLabel, target):
        block = self.blocks.get(target.group_name)
        if block is None or label.team not in block.labels:
            return

        current_slot = self._find_current_slot(block, label)

        if isinstance(target, SlotFrame):
            if target is current_slot:
                return

            if target.team_label is not None:
                displaced = target.clear()
                if current_slot is not None:
                    current_slot.clear()
                    current_slot.set_team(displaced)
                else:
                    displaced.pack(in_=block.pool, pady=2, padx=4, fill='x')

            if current_slot is not None:
                current_slot.team_label = None
                current_slot.placeholder.pack(expand=True, fill='both')

            label.pack_forget()
            target.set_team(label)

        elif isinstance(target, PoolFrame):
            if current_slot is None:
                return
            current_slot.clear()
            label.pack_forget()
            label.pack(in_=target, pady=2, padx=4, fill='x')

        self._update_status()
        if self.on_change:
            self.on_change()

    def reset_all(self):
        for block in self.blocks.values():
            block.reset()
        self._update_status()
        if self.on_change:
            self.on_change()

    def _update_status(self):
        complete = sum(1 for b in self.blocks.values() if b.get_standings() is not None)
        total = len(self.blocks)
        self.status_label.configure(text=f'Готово групп: {complete} / {total}')

    def is_complete(self) -> bool:
        return all(b.get_standings() is not None for b in self.blocks.values())

    def build_tournament(self) -> Tournament | None:
        if not self.is_complete():
            return None

        groups_for_tournament = {name: teams for name, teams in self.groups_data.items()}
        tournament = Tournament(groups_for_tournament)

        for group_name, block in self.blocks.items():
            standings = block.get_standings()
            t1, t2, t3, t4 = standings
            g = tournament.groups[group_name]
            g.set_result(t1, t2, 1, 0)
            g.set_result(t1, t3, 2, 0)
            g.set_result(t1, t4, 3, 0)
            g.set_result(t2, t3, 1, 0)
            g.set_result(t2, t4, 2, 0)
            g.set_result(t3, t4, 1, 0)

        return tournament