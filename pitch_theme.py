"""
Фоновое оформление в стиле "вид на футбольное поле сверху".

Даёт два инструмента:

1. repaint(canvas, orientation) — рисует травяной фон с чередующимися
   полосами и полную разметку поля (внешняя линия, центральная линия,
   центральный круг, штрафные/вратарские площади с дугами) прямо на Canvas,
   позади всех остальных элементов (tag_lower). orientation:
     - 'vertical'   — ворота сверху и снизу (для вертикально
                      прокручиваемых вкладок групп),
     - 'horizontal' — ворота слева и справа (для горизонтальной сетки
                      плейофф: путь от 1/16 финала к Финалу естественно
                      читается как путь от одних ворот к другим).

   ВАЖНО: если внутри canvas есть непрозрачный Frame (create_window),
   занимающий всю область, разметка под ним не будет видна. Поэтому
   repaint() в первую очередь задаёт ЦВЕТ фона canvas/контейнеров (зелёные
   тона травы) — это видно везде, а сама нарисованная разметка видна
   в полях/отступах вокруг и между виджетами.

2. PitchBand — декоративный Canvas-виджет "полоса разметки", который можно
   вставить как обычную строку в grid-раскладку (между карточками групп).
   Он гарантированно виден (это обычный дочерний виджет, а не рисунок
   позади другого виджета) и рисует либо центральный круг с центральной
   линией ('center'), либо вратарскую+штрафную площадь с дугой
   ('goal_top' / 'goal_bottom').
"""

import tkinter as tk

# Цвета "травы" и линий разметки
GRASS_DARK = '#1f4d2e'
GRASS_LIGHT = '#26613a'
LINE_COLOR = '#eef7ee'
LINE_WIDTH = 2

PITCH_TAG = 'pitch_bg'


# ---------------------------------------------------------------------------
# Рисование фона на основном Canvas
# ---------------------------------------------------------------------------

def _stripes(canvas, width, height, n, vertical_stripes):
    """Рисует n чередующихся прямоугольников-полос травы."""
    if n <= 0:
        return
    if vertical_stripes:
        step = width / n
        for i in range(n):
            color = GRASS_LIGHT if i % 2 == 0 else GRASS_DARK
            x0, x1 = i * step, (i + 1) * step
            canvas.create_rectangle(x0, 0, x1, height, fill=color, width=0, tags=PITCH_TAG)
    else:
        step = height / n
        for i in range(n):
            color = GRASS_LIGHT if i % 2 == 0 else GRASS_DARK
            y0, y1 = i * step, (i + 1) * step
            canvas.create_rectangle(0, y0, width, y1, fill=color, width=0, tags=PITCH_TAG)


def _draw_goal_block(canvas, cx, edge, size, axis, direction, line_width=LINE_WIDTH):
    """
    Рисует штрафную+вратарскую площадь с дугой у одного края поля.

    cx     — координата центра по оси, перпендикулярной направлению "вглубь".
    edge   — координата самого края поля (линия ворот).
    size   — характерный размер (используется для масштабирования площадей).
    axis   — 'y' если ворота сверху/снизу (площадь "растёт" по Y),
             'x' если ворота слева/справа (площадь "растёт" по X).
    direction — +1 или -1: в какую сторону от edge "растёт" площадь.
    """
    pen_depth = size * 0.16
    pen_width = size * 0.5
    goal_depth = pen_depth * 0.45
    goal_width = size * 0.22
    arc_r = pen_depth * 0.85
    dot_r = 3

    if axis == 'y':
        pen_far = edge + direction * pen_depth
        goal_far = edge + direction * goal_depth
        canvas.create_rectangle(cx - pen_width / 2, edge, cx + pen_width / 2, pen_far,
                                 outline=LINE_COLOR, width=line_width, tags=PITCH_TAG)
        canvas.create_rectangle(cx - goal_width / 2, edge, cx + goal_width / 2, goal_far,
                                 outline=LINE_COLOR, width=line_width, tags=PITCH_TAG)
        dot_y = edge + direction * pen_depth * 0.72
        canvas.create_oval(cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r,
                            fill=LINE_COLOR, outline='', tags=PITCH_TAG)
        start = 0 if direction > 0 else 180
        canvas.create_arc(cx - arc_r, dot_y - arc_r, cx + arc_r, dot_y + arc_r,
                           start=start, extent=180, style='arc',
                           outline=LINE_COLOR, width=line_width, tags=PITCH_TAG)
    else:  # axis == 'x'
        pen_far = edge + direction * pen_depth
        goal_far = edge + direction * goal_depth
        canvas.create_rectangle(edge, cx - pen_width / 2, pen_far, cx + pen_width / 2,
                                 outline=LINE_COLOR, width=line_width, tags=PITCH_TAG)
        canvas.create_rectangle(edge, cx - goal_width / 2, goal_far, cx + goal_width / 2,
                                 outline=LINE_COLOR, width=line_width, tags=PITCH_TAG)
        dot_x = edge + direction * pen_depth * 0.72
        canvas.create_oval(dot_x - dot_r, cx - dot_r, dot_x + dot_r, cx + dot_r,
                            fill=LINE_COLOR, outline='', tags=PITCH_TAG)
        start = 90 if direction > 0 else 270
        canvas.create_arc(dot_x - arc_r, cx - arc_r, dot_x + arc_r, cx + arc_r,
                           start=start, extent=180, style='arc',
                           outline=LINE_COLOR, width=line_width, tags=PITCH_TAG)


def draw_vertical_pitch(canvas, width, height):
    """Поле "вертикально": ворота сверху и снизу, центральная линия горизонтальна."""
    n_stripes = max(6, int(height / 90))
    _stripes(canvas, width, height, n_stripes, vertical_stripes=False)

    margin = min(width, height) * 0.015
    canvas.create_rectangle(margin, margin, width - margin, height - margin,
                             outline=LINE_COLOR, width=LINE_WIDTH, tags=PITCH_TAG)

    cx, cy = width / 2, height / 2
    canvas.create_line(margin, cy, width - margin, cy,
                        fill=LINE_COLOR, width=LINE_WIDTH, tags=PITCH_TAG)

    radius = min(width, height) * 0.06
    canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                        outline=LINE_COLOR, width=LINE_WIDTH, tags=PITCH_TAG)
    canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=LINE_COLOR, outline='', tags=PITCH_TAG)

    size = min(width, height)
    _draw_goal_block(canvas, cx, margin, size, axis='y', direction=+1)
    _draw_goal_block(canvas, cx, height - margin, size, axis='y', direction=-1)


def draw_horizontal_pitch(canvas, width, height):
    """Поле "горизонтально": ворота слева и справа, центральная линия вертикальна."""
    n_stripes = max(6, int(width / 120))
    _stripes(canvas, width, height, n_stripes, vertical_stripes=True)

    margin = min(width, height) * 0.02
    canvas.create_rectangle(margin, margin, width - margin, height - margin,
                             outline=LINE_COLOR, width=LINE_WIDTH, tags=PITCH_TAG)

    cx, cy = width / 2, height / 2
    canvas.create_line(cx, margin, cx, height - margin,
                        fill=LINE_COLOR, width=LINE_WIDTH, tags=PITCH_TAG)

    radius = min(width, height) * 0.12
    canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                        outline=LINE_COLOR, width=LINE_WIDTH, tags=PITCH_TAG)
    canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=LINE_COLOR, outline='', tags=PITCH_TAG)

    size = min(width, height)
    _draw_goal_block(canvas, cy, margin, size, axis='x', direction=+1)
    _draw_goal_block(canvas, cy, width - margin, size, axis='x', direction=-1)


def repaint(canvas: tk.Canvas, orientation: str = 'vertical'):
    """
    Перерисовывает травяной фон и разметку на canvas, покрывая всю
    прокручиваемую область (scrollregion), и обновляет сам scrollregion.

    Вызывать из обработчиков <Configure> внутреннего фрейма и canvas.
    """
    canvas.delete(PITCH_TAG)

    bbox = canvas.bbox('all')
    width = canvas.winfo_width()
    height = canvas.winfo_height()
    if bbox:
        width = max(width, bbox[2])
        height = max(height, bbox[3])

    if width <= 1 or height <= 1:
        return

    if orientation == 'horizontal':
        draw_horizontal_pitch(canvas, width, height)
    else:
        draw_vertical_pitch(canvas, width, height)

    canvas.tag_lower(PITCH_TAG)
    canvas.configure(scrollregion=(0, 0, width, height))


# ---------------------------------------------------------------------------
# Декоративная полоса разметки как обычный виджет в grid-раскладке
# ---------------------------------------------------------------------------

class PitchBand(tk.Canvas):
    """
    Горизонтальная декоративная полоса травы с разметкой, для вставки как
    обычная строка в grid-раскладку (между карточками групп).

    kind:
      - 'center'     — центральная линия + центральный круг
      - 'goal_top'   — вратарская/штрафная площадь, "открытая" вниз
                       (как если смотреть на верхние ворота поля)
      - 'goal_bottom'— то же, "открытая" вверх (нижние ворота поля)
    """

    def __init__(self, master, kind: str = 'center', height: int = 90, **kwargs):
        kwargs.setdefault('highlightthickness', 0)
        kwargs.setdefault('bg', GRASS_DARK)
        super().__init__(master, height=height, **kwargs)
        self.kind = kind
        self.bind('<Configure>', self._redraw)

    def _redraw(self, event=None):
        width = self.winfo_width()
        height = self.winfo_height()
        self.delete('all')
        if width <= 1 or height <= 1:
            return

        n = max(4, int(width / 80))
        for i in range(n):
            color = GRASS_LIGHT if i % 2 == 0 else GRASS_DARK
            step = width / n
            self.create_rectangle(i * step, 0, (i + 1) * step, height, fill=color, width=0)

        cx = width / 2

        if self.kind == 'center':
            self.create_line(0, height / 2, width, height / 2, fill=LINE_COLOR, width=LINE_WIDTH)
            radius = min(width * 0.06, height * 0.7)
            self.create_oval(cx - radius, height / 2 - radius, cx + radius, height / 2 + radius,
                              outline=LINE_COLOR, width=LINE_WIDTH)
            self.create_oval(cx - 3, height / 2 - 3, cx + 3, height / 2 + 3,
                              fill=LINE_COLOR, outline='')
        elif self.kind == 'goal_top':
            self._draw_goal(width, height, cx, edge_y=0, direction=+1)
        elif self.kind == 'goal_bottom':
            self._draw_goal(width, height, cx, edge_y=height, direction=-1)

    def _draw_goal(self, width, height, cx, edge_y, direction):
        size = max(width, height * 4)
        pen_depth = min(height * 0.9, size * 0.10)
        pen_width = min(width * 0.5, size * 0.35)
        goal_depth = pen_depth * 0.45
        goal_width = pen_width * 0.45
        arc_r = pen_depth * 0.9
        dot_r = 3

        pen_far = edge_y + direction * pen_depth
        goal_far = edge_y + direction * goal_depth

        self.create_rectangle(cx - pen_width / 2, edge_y, cx + pen_width / 2, pen_far,
                               outline=LINE_COLOR, width=LINE_WIDTH)
        self.create_rectangle(cx - goal_width / 2, edge_y, cx + goal_width / 2, goal_far,
                               outline=LINE_COLOR, width=LINE_WIDTH)

        dot_y = edge_y + direction * pen_depth * 0.72
        self.create_oval(cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r,
                          fill=LINE_COLOR, outline='')

        start = 0 if direction > 0 else 180
        self.create_arc(cx - arc_r, dot_y - arc_r, cx + arc_r, dot_y + arc_r,
                         start=start, extent=180, style='arc',
                         outline=LINE_COLOR, width=LINE_WIDTH)
