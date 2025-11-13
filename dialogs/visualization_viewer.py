import tkinter as tk
from tkinter import ttk, messagebox
from theme import BLUE_BG, BG_MAIN

from src.forecast import Forecast
from modules.downloader import trigger_file_download

class VisualizationViewer:
    """
    Слайдер із трьома зображеннями:
      - Кнопки ◀ ▶ для навігації між 1/3
      - Прокрутка: вертикальна й горизонтальна (канва з scrollregion)
      - Кнопка "Завантажити" для поточного слайда (поки заглушка)
    """

    def __init__(self, master, *, forecast_title="Візуалізація"):
        self.master = master
        self.index = 0  # 0..2

        self.images = [
            Forecast.getImagePath(forecast_title, 'actuals'),
            Forecast.getImagePath(forecast_title, 'forecast'),
            Forecast.getImagePath(forecast_title, 'comparison')
        ]

        # кеш об'єктів PhotoImage, щоб GC не прибирав
        self._photos = [None, None, None]

        # ---- Вікно
        self.top = tk.Toplevel(master)
        self.top.title(forecast_title or "Візуалізація")
        self.top.transient(master); self.top.grab_set()
        self.top.configure(bg=BLUE_BG)
        self.top.resizable(True, True)

        w, h = 900, 640
        self.top.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - w) // 2
        y = master.winfo_y() + (master.winfo_height() - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        root = tk.Frame(self.top, bg=BLUE_BG, bd=2, relief="groove")
        root.pack(fill="both", expand=True, padx=12, pady=12)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        # ---- Панель керування (slider controls)
        ctrl = tk.Frame(root, bg=BLUE_BG)
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Button(ctrl, text="◀", width=3, command=self.prev).pack(side="left")
        self.idx_label = tk.Label(ctrl, text="1 / 3", bg=BLUE_BG)
        self.idx_label.pack(side="left", padx=8)
        tk.Button(ctrl, text="▶", width=3, command=self.next).pack(side="left", padx=(0,8))
        tk.Button(ctrl, text="Завантажити", bg=BG_MAIN, command=self._download_stub)\
            .pack(side="right")

        # ---- Прокручуваний Canvas
        wrap = tk.Frame(root, bg=BLUE_BG)
        wrap.grid(row=1, column=0, sticky="nsew")

        self.canvas = tk.Canvas(wrap, bg="white", highlightthickness=0)
        self.hsb = ttk.Scrollbar(wrap, orient="horizontal", command=self.canvas.xview)
        self.vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hsb.set, yscrollcommand=self.vsb.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)

        # події для зручного скролу мишкою
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)         # Windows/macOS вертикально
        self.canvas.bind("<Shift-MouseWheel>", self._on_shiftwheel)   # з Shift — горизонтально

        # показати перший слайд
        self._show_current()

        # також міняємо розмітку при resize, щоб не «різало» заглушку
        self.top.bind("<Configure>", lambda e: self._refresh_scrollregion())

    # ---------- slider API ----------
    '''
    def set_images(self, path1="", path2="", path3=""):
        self.img_path1, self.img_path2, self.img_path3 = path1 or "", path2 or "", path3 or ""
        self._photos = [None, None, None]
        self.index = 0
        self._show_current()
    '''

    def next(self):
        self.index = (self.index + 1) % 3
        self._show_current()

    def prev(self):
        self.index = (self.index - 1) % 3
        self._show_current()

    # ---------- rendering ----------
    def _show_current(self):
        self.idx_label.config(text=f"{self.index + 1} / {len(self.images)}")
        self.canvas.delete("all")

        path = self.images[self.index]
        if path:
            try:
                # стандартний PhotoImage (PNG/GIF). Для JPG знадобиться PIL.
                img = tk.PhotoImage(file=path)
                self._photos[self.index] = img
                # малюємо з верхнього лівого кута, щоб скролл працював інтуїтивно
                self.canvas.create_image(0, 0, image=img, anchor="nw")
                # область прокрутки рівна розміру зображення
                self.canvas.config(scrollregion=(0, 0, img.width(), img.height()))
                return
            except Exception as e:
                self._draw_placeholder(f"Не вдалося відкрити\n{path}\n{e}")
        else:
            self._draw_placeholder("(Немає зображення)")

    def _draw_placeholder(self, text):
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 300)
        h = max(self.canvas.winfo_height(), 200)
        pad = 20
        self.canvas.create_rectangle(pad, pad, w - pad, h - pad, outline="#c0c0c0")
        self.canvas.create_text(w // 2, h // 2, text=text, fill="#888", anchor="center")
        self.canvas.config(scrollregion=(0, 0, w, h))

    def _refresh_scrollregion(self):
        # якщо показуємо зображення — scrollregion вже виставлено; для заглушки — підлаштуємо
        if not any(self._photos):
            self._draw_placeholder("(Немає зображення)")

    # ---------- scrolling helpers ----------
    def _on_mousewheel(self, event):
        # Windows/macOS: вертикальна прокрутка
        delta = int(-1 * (event.delta / 120))  # кроки
        self.canvas.yview_scroll(delta, "units")

    def _on_shiftwheel(self, event):
        # із Shift крутимо горизонтально
        delta = int(-1 * (event.delta / 120))
        self.canvas.xview_scroll(delta, "units")

    # ---------- download stub ----------
    def _download_stub(self):
        image_path = self.images[self.index]
        trigger_file_download(image_path, self.master)