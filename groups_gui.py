"""
GUI вкладки "Группы" — базовая версия.

Для каждой из 12 групп показываются 4 команды, которые можно перетащить
мышью в 4 слота ("1 место" .. "4 место"). На основе итогового распределения
формируется Tournament с фиктивными результатами матчей, которые дают
ровно такую таблицу (1-е место - 9 очков, 2-е - 6, 3-е - 3, 4-е - 0,
без голов), чтобы bracket_logic мог построить сетку плейофф.

UI: вертикальный скроллируемый список из 12 групп. В каждой группе слева —
"пул" нераспределённых команд (перетаскиваемые лейблы), справа — 4 слота
с подписями "1 место".."4 место". Перетаскивание реализовано вручную через
события <ButtonPress-1> / <B1-Motion> / <ButtonRelease-1> (без внешних
библиотек).
"""

import tkinter as tk
from tkinter import ttk

from group_stage import Tournament


SLOT_LABELS = ['1 место', '2 место', '3 место', '4 место']


class DraggableLabel(tk.Label):
    """Лейбл команды, который можно перетаскивать между контейнерами."""

    def __init__(self, master, text, controller, **kwargs):
        super().__init__(
            master, text=text, relief='raised', borderwidth=2,
            padx=8, pady=4, bg='#ffffff', cursor='hand2', **kwargs
        )
        self.team = text
        self.controller = controller  # GroupsTab — для доступа к общему состоянию
        self._drag_data = {'x': 0, 'y': 0, 'item': None}

        self.bind('<ButtonPress-1>', self._on_press)
        self.bind('<B1-Motion>', self._on_motion)
        self.bind('<ButtonRelease-1>', self._on_release)

    # ------------------------------------------------------------------
    def _on_press(self, event):
        self._drag_data['x'] = event.x_root
        self._drag_data['y'] = event.y_root
        self.lift()
        # Создаём "плавающую" копию, которая будет следовать за курсором
        self._floating = tk.Toplevel(self)
        self._floating.overrideredirect(True)
        self._floating.attributes('-alpha', 0.85)
        lbl = tk.Label(self._floating, text=self.team, relief='raised',
                        borderwidth=2, padx=8, pady=4, bg='#cde6ff')
        lbl.pack()
        self._update_floating_pos(event)
        self.configure(bg='#dddddd')

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
        self.configure(bg='#ffffff')

        # Определяем виджет под курсором
        widget = self.winfo_containing(event.x_root, event.y_root)
        target = self._find_drop_target(widget)
        if target is not None:
            self.controller.handle_drop(self, target)

    @staticmethod
    def _find_drop_target(widget):
        """Поднимается по иерархии виджетов, ищет SlotFrame или PoolFrame."""
        w = widget
        while w is not None:
            if isinstance(w, (SlotFrame, PoolFrame)):
                return w
            w = getattr(w, 'master', None)
        return None


class SlotFrame(ttk.Frame):
    """Один слот ("1 место" и т.п.) — может содержать максимум одну команду."""

    def __init__(self, master, group_name: str, slot_index: int, label_text: str, **kwargs):
        super().__init__(master, relief='sunken', borderwidth=2, width=160, height=40, **kwargs)
        self.group_name = group_name
        self.slot_index = slot_index  # 0..3
        self.team_label = None  # DraggableLabel внутри слота, либо None

        self.placeholder = ttk.Label(self, text=label_text, foreground='gray')
        self.placeholder.pack(expand=True)

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
            self.placeholder.pack(expand=True)
        return old


class PoolFrame(ttk.Frame):
    """Контейнер нераспределённых команд группы."""

    def __init__(self, master, group_name: str, **kwargs):
        super().__init__(master, relief='groove', borderwidth=1, **kwargs)
        self.group_name = group_name


class GroupBlock(ttk.Frame):
    """Визуальный блок одной группы: название + пул + 4 слота."""

    def __init__(self, master, group_name: str, teams: list[str], controller, **kwargs):
        super().__init__(master, relief='ridge', borderwidth=1, padding=10, **kwargs)
        self.group_name = group_name
        self.controller = controller

        title = ttk.Label(self, text=f'Группа {group_name}', font=('TkDefaultFont', 11, 'bold'))
        title.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 6))

        ttk.Label(self, text='Команды (перетащите вправо):').grid(row=1, column=0, sticky='w')
        ttk.Label(self, text='Итоговые места:').grid(row=1, column=1, sticky='w', padx=(30, 0))

        self.pool = PoolFrame(self, group_name)
        self.pool.grid(row=2, column=0, sticky='nw', padx=(0, 30), pady=4)

        slots_frame = ttk.Frame(self)
        slots_frame.grid(row=2, column=1, sticky='nw')

        self.slots: list[SlotFrame] = []
        for i, label_text in enumerate(SLOT_LABELS):
            row_frame = ttk.Frame(slots_frame)
            row_frame.pack(anchor='w', pady=2)
            ttk.Label(row_frame, text=f'{label_text}:', width=10).pack(side='left')
            slot = SlotFrame(row_frame, group_name, i, '(пусто)')
            slot.pack(side='left')
            self.slots.append(slot)

        # Изначально все команды в пуле.
        # ВАЖНО: master лейблов — сам GroupBlock (общий предок пула и слотов),
        # а не PoolFrame, иначе pack(in_=SlotFrame) упадёт с TclError,
        # так как Tk требует, чтобы 'in_' был master-ом или его потомком.
        self.labels: dict[str, DraggableLabel] = {}
        for team in teams:
            lbl = DraggableLabel(self, team, controller)
            lbl.pack(in_=self.pool, pady=2, padx=4, fill='x')
            self.labels[team] = lbl

    def get_standings(self) -> list[str] | None:
        """Возвращает список команд по местам [1,2,3,4] или None, если не все слоты заполнены."""
        teams = []
        for slot in self.slots:
            if slot.team_label is None:
                return None
            teams.append(slot.team_label.team)
        return teams

    def reset(self):
        """Возвращает все команды обратно в пул."""
        for slot in self.slots:
            label = slot.clear()
            if label is not None:
                label.pack(in_=self.pool, pady=2, padx=4, fill='x')


class GroupsTab(ttk.Frame):
    """Вкладка с 12 группами, прокручиваемая по вертикали."""

    def __init__(self, master, groups_data: dict[str, list[str]], on_change=None, *args, **kwargs):
        """
        groups_data: {group_name: [team1, team2, team3, team4]}
        on_change: опциональный callback(), вызывается при любом изменении
                   расстановки (для уведомления других частей приложения).
        """
        super().__init__(master, *args, **kwargs)
        self.groups_data = groups_data
        self.on_change = on_change
        self.blocks: dict[str, GroupBlock] = {}

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        top_bar = ttk.Frame(self)
        top_bar.pack(side='top', fill='x', padx=10, pady=8)

        ttk.Label(
            top_bar,
            text='Перетащите названия команд из левого списка в слоты с 1 по 4 место.',
        ).pack(side='left')

        ttk.Button(top_bar, text='Сбросить всё', command=self.reset_all).pack(side='right')
        self.status_label = ttk.Label(top_bar, text='')
        self.status_label.pack(side='right', padx=10)

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(side='top', fill='both', expand=True)

        self.canvas = tk.Canvas(canvas_frame, borderwidth=0, highlightthickness=0)
        v_scroll = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=v_scroll.set)

        self.canvas.pack(side='left', fill='both', expand=True)
        v_scroll.pack(side='right', fill='y')

        self.inner_frame = ttk.Frame(self.canvas)
        self.inner_frame_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')

        self.inner_frame.bind('<Configure>', self._on_inner_configure)
        self.canvas.bind('<Configure>', self._on_canvas_resize)

        # Колёсико мыши
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)       # Windows / macOS
        self.canvas.bind_all('<Button-4>', self._on_mousewheel_linux)   # Linux up
        self.canvas.bind_all('<Button-5>', self._on_mousewheel_linux)   # Linux down

        for group_name, teams in self.groups_data.items():
            block = GroupBlock(self.inner_frame, group_name, teams, self)
            block.pack(fill='x', padx=10, pady=6)
            self.blocks[group_name] = block

        self._update_status()

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_resize(self, event):
        self.canvas.itemconfigure(self.inner_frame_id, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def _on_mousewheel_linux(self, event):
        delta = -1 if event.num == 4 else 1
        self.canvas.yview_scroll(delta, 'units')

    # ------------------------------------------------------------------
    def _find_current_slot(self, block: 'GroupBlock', label: DraggableLabel) -> 'SlotFrame | None':
        """Возвращает SlotFrame, в котором сейчас находится label, либо None (если в пуле)."""
        for slot in block.slots:
            if slot.team_label is label:
                return slot
        return None

    def handle_drop(self, label: DraggableLabel, target):
        """Обрабатывает перетаскивание лейбла команды в новый контейнер."""
        block = self.blocks.get(target.group_name)
        if block is None or label.team not in block.labels:
            return

        current_slot = self._find_current_slot(block, label)

        if isinstance(target, SlotFrame):
            if target is current_slot:
                # Перетащили на то же место — ничего не делаем
                return

            if target.team_label is not None:
                # Целевой слот занят другой командой — вытесняем её
                displaced = target.clear()
                if current_slot is not None:
                    # В целевом слоте была команда, а перетаскиваемая команда
                    # была в другом слоте -> меняем их местами
                    current_slot.clear()
                    current_slot.set_team(displaced)
                else:
                    displaced.pack(in_=block.pool, pady=2, padx=4, fill='x')

            # Освобождаем исходное место label
            if current_slot is not None:
                current_slot.team_label = None
                current_slot.placeholder.pack(expand=True)

            label.pack_forget()
            target.set_team(label)

        elif isinstance(target, PoolFrame):
            if current_slot is None:
                # Уже в пуле — ничего делать не нужно
                return

            current_slot.clear()
            label.pack_forget()
            label.pack(in_=target, pady=2, padx=4, fill='x')

        self._update_status()
        if self.on_change:
            self.on_change()

    # ------------------------------------------------------------------
    def reset_all(self):
        for block in self.blocks.values():
            block.reset()
        self._update_status()
        if self.on_change:
            self.on_change()

    def _update_status(self):
        complete = sum(1 for b in self.blocks.values() if b.get_standings() is not None)
        total = len(self.blocks)
        self.status_label.configure(text=f'Распределено групп: {complete} / {total}')

    # ------------------------------------------------------------------
    def is_complete(self) -> bool:
        return all(b.get_standings() is not None for b in self.blocks.values())

    def build_tournament(self) -> Tournament | None:
        """
        Строит объект Tournament на основе выбранных мест.

        Поскольку базовая версия не предполагает реальных счетов матчей,
        генерируются "синтетические" результаты, которые гарантированно
        дают команде на месте N очки/разницу голов, строго большие,
        чем у команды на месте N+1 (9/6/3/0 очков соответственно),
        чтобы итоговая таблица standings() совпадала с выбранным порядком.

        Синтетические результаты кругового турнира для порядка [t1,t2,t3,t4]
        (t1 - 1 место, ..., t4 - 4 место):
          t1-t2: 1:0   t1-t3: 2:0   t1-t4: 3:0
          t2-t3: 1:0   t2-t4: 2:0
          t3-t4: 1:0
        Итоговые очки: t1=9, t2=6, t3=3, t4=0 — порядок гарантирован
        независимо от тай-брейков.
        """
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


if __name__ == '__main__':
    from data import GROUPS

    root = tk.Tk()
    root.title('Тест: вкладка групп ЧМ-2026 (базовая версия)')
    root.geometry('900x800')

    def on_change():
        print('Изменение расстановки')

    tab = GroupsTab(root, GROUPS, on_change=on_change)
    tab.pack(fill='both', expand=True)

    root.mainloop()
